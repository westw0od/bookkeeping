package com.westw0od.bookkeeping;

import android.content.Intent;
import android.content.pm.PackageInfo;
import android.content.pm.PackageManager;
import android.content.pm.Signature;
import android.net.Uri;
import android.os.Build;
import android.os.SystemClock;
import android.provider.Settings;
import androidx.core.content.FileProvider;
import com.getcapacitor.JSObject;
import com.getcapacitor.Plugin;
import com.getcapacitor.PluginCall;
import com.getcapacitor.PluginMethod;
import com.getcapacitor.annotation.CapacitorPlugin;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.InputStream;
import java.net.HttpURLConnection;
import java.net.URI;
import java.security.MessageDigest;
import java.util.Arrays;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.atomic.AtomicBoolean;

@CapacitorPlugin(name = "AppUpdater")
public class AppUpdaterPlugin extends Plugin {
    private final ExecutorService worker = Executors.newSingleThreadExecutor();
    private final AtomicBoolean downloading = new AtomicBoolean(false);
    private final AtomicBoolean cancelled = new AtomicBoolean(false);
    private volatile HttpURLConnection connection;
    private volatile ReadyPackage ready;

    private static final class ReadyPackage {
        final File file;
        final int version;
        final String hash;
        final long size;
        ReadyPackage(File file, int version, String hash, long size) {
            this.file = file; this.version = version; this.hash = hash; this.size = size;
        }
    }

    private int packageFlags() {
        return Build.VERSION.SDK_INT >= 28 ? PackageManager.GET_SIGNING_CERTIFICATES : PackageManager.GET_SIGNATURES;
    }

    private long version(PackageInfo info) {
        return Build.VERSION.SDK_INT >= 28 ? info.getLongVersionCode() : info.versionCode;
    }

    @PluginMethod
    public void getInfo(PluginCall call) {
        try {
            PackageInfo info = getContext().getPackageManager().getPackageInfo(getContext().getPackageName(), 0);
            JSObject result = new JSObject();
            result.put("versionCode", version(info));
            result.put("versionName", info.versionName);
            result.put("sdkInt", Build.VERSION.SDK_INT);
            result.put("applicationId", getContext().getPackageName());
            call.resolve(result);
        } catch (Exception ignored) { call.reject("无法读取当前应用版本"); }
    }

    @PluginMethod
    public void download(PluginCall call) {
        if (!downloading.compareAndSet(false, true)) { call.reject("更新包正在下载"); return; }
        cancelled.set(false);
        worker.execute(() -> {
            File partial = null;
            File target = null;
            try {
                int code = call.getInt("versionCode", 0);
                String hash = call.getString("sha256", "");
                // JSONObject decodes APK sizes below 100 MiB as Integer, not Long.
                long size = call.getInt("sizeBytes", 0);
                URI uri = UpdatePolicy.downloadUri(call.getString("serverUrl", ""), code, hash, size);
                PackageInfo installed = getContext().getPackageManager().getPackageInfo(getContext().getPackageName(), 0);
                if (code <= version(installed)) throw new IllegalArgumentException("当前已是该版本或更新版本");
                File folder = new File(getContext().getCacheDir(), "updates");
                if (!folder.isDirectory() && !folder.mkdirs()) throw new IllegalStateException("无法创建下载缓存");
                ready = null;
                File[] old = folder.listFiles();
                if (old != null) for (File item : old) {
                    if (item.getName().matches("bookkeeping-[0-9]+\\.apk(?:\\.part)?")) item.delete();
                }
                target = new File(folder, "bookkeeping-" + code + ".apk");
                partial = new File(folder, target.getName() + ".part");
                connection = (HttpURLConnection) uri.toURL().openConnection();
                connection.setInstanceFollowRedirects(false);
                connection.setConnectTimeout(15000);
                connection.setReadTimeout(15000);
                connection.setRequestProperty("Accept", "application/vnd.android.package-archive");
                connection.setRequestProperty("Accept-Encoding", "identity");
                if (connection.getResponseCode() != 200) throw new IllegalStateException("服务器暂时无法提供该更新包，请重新检查更新");
                String lengthHeader = connection.getHeaderField("Content-Length");
                long advertised = lengthHeader == null ? -1 : Long.parseLong(lengthHeader);
                if (advertised >= 0 && advertised != size) throw new IllegalStateException("更新包大小不一致，请重新检查更新");
                MessageDigest digest = MessageDigest.getInstance("SHA-256");
                long received = 0, started = SystemClock.elapsedRealtime(), lastProgress = 0;
                progress(0, size);
                try (InputStream input = connection.getInputStream(); FileOutputStream output = new FileOutputStream(partial)) {
                    byte[] buffer = new byte[65536];
                    int count;
                    while ((count = input.read(buffer)) != -1) {
                        if (cancelled.get() || Thread.currentThread().isInterrupted()) throw new InterruptedException();
                        received += count;
                        if (received > size || SystemClock.elapsedRealtime() - started > 180000) throw new IllegalStateException("下载超时或更新包大小异常，请重试");
                        output.write(buffer, 0, count);
                        digest.update(buffer, 0, count);
                        if (SystemClock.elapsedRealtime() - lastProgress > 150) {
                            progress(received, size); lastProgress = SystemClock.elapsedRealtime();
                        }
                    }
                    output.getFD().sync();
                }
                if (cancelled.get()) throw new InterruptedException();
                if (received != size || !UpdatePolicy.matchesHash(digest.digest(), hash)) throw new IllegalStateException("更新包校验失败，请重新下载");
                if (!partial.renameTo(target)) throw new IllegalStateException("无法保存更新包");
                ReadyPackage candidate = new ReadyPackage(target, code, hash, size);
                verifyArchive(candidate);
                ready = candidate;
                progress(size, size);
                call.resolve(new JSObject().put("ready", true));
            } catch (Exception error) {
                if (partial != null) partial.delete();
                if (target != null) target.delete();
                String message = cancelled.get() ? "已取消下载" :
                    error instanceof IllegalArgumentException || error instanceof IllegalStateException ? error.getMessage() : "下载失败，请检查网络后重试";
                call.reject(message, cancelled.get() ? "CANCELLED" : "UPDATE_FAILED");
            } finally {
                if (connection != null) connection.disconnect();
                connection = null;
                downloading.set(false);
            }
        });
    }

    private Signature[] signers(PackageInfo info) {
        if (Build.VERSION.SDK_INT >= 28) return info.signingInfo == null ? null : info.signingInfo.getApkContentsSigners();
        return info.signatures;
    }

    private void verifyArchive(ReadyPackage candidate) throws Exception {
        if (!candidate.file.isFile() || candidate.file.length() != candidate.size) throw new IllegalStateException("更新包已失效，请重新下载");
        MessageDigest digest = MessageDigest.getInstance("SHA-256");
        try (InputStream input = new FileInputStream(candidate.file)) {
            byte[] buffer = new byte[65536]; int count;
            while ((count = input.read(buffer)) != -1) digest.update(buffer, 0, count);
        }
        if (!UpdatePolicy.matchesHash(digest.digest(), candidate.hash)) throw new IllegalStateException("更新包校验失败，请重新下载");
        PackageManager manager = getContext().getPackageManager();
        PackageInfo archive = manager.getPackageArchiveInfo(candidate.file.getAbsolutePath(), packageFlags());
        PackageInfo installed = manager.getPackageInfo(getContext().getPackageName(), packageFlags());
        if (archive == null || !getContext().getPackageName().equals(archive.packageName) ||
            version(archive) != candidate.version || version(archive) <= version(installed)) {
            throw new IllegalStateException("更新包的应用或版本不匹配");
        }
        if (Build.VERSION.SDK_INT >= 24 && archive.applicationInfo != null && archive.applicationInfo.minSdkVersion > Build.VERSION.SDK_INT) {
            throw new IllegalStateException("此版本不支持当前 Android 系统");
        }
        Signature[] expected = signers(installed), actual = signers(archive);
        if (expected == null || actual == null || expected.length == 0 || expected.length != actual.length ||
            !Arrays.asList(expected).containsAll(Arrays.asList(actual))) {
            throw new IllegalStateException("更新包签名不匹配，已阻止安装");
        }
    }

    private void progress(long received, long total) {
        JSObject value = new JSObject();
        value.put("received", received); value.put("total", total);
        value.put("percent", (int) (received * 100 / total));
        notifyListeners("downloadProgress", value);
    }

    @PluginMethod
    public void cancelDownload(PluginCall call) {
        cancelled.set(true);
        if (connection != null) connection.disconnect();
        call.resolve();
    }

    @PluginMethod
    public void install(PluginCall call) {
        ReadyPackage candidate = ready;
        if (candidate == null) { call.reject("请先下载更新包"); return; }
        worker.execute(() -> {
            try {
                verifyArchive(candidate);
                getActivity().runOnUiThread(() -> {
                    try {
                        if (Build.VERSION.SDK_INT >= 26 && !getContext().getPackageManager().canRequestPackageInstalls()) {
                            Intent settings = new Intent(Settings.ACTION_MANAGE_UNKNOWN_APP_SOURCES, Uri.parse("package:" + getContext().getPackageName()));
                            getActivity().startActivity(settings);
                            call.resolve(new JSObject().put("status", "permission_required"));
                            return;
                        }
                        Uri uri = FileProvider.getUriForFile(getContext(), getContext().getPackageName() + ".fileprovider", candidate.file);
                        Intent intent = new Intent(Intent.ACTION_VIEW);
                        intent.setDataAndType(uri, "application/vnd.android.package-archive");
                        intent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION);
                        getActivity().startActivity(intent);
                        call.resolve(new JSObject().put("status", "installer_opened"));
                    } catch (Exception ignored) { call.reject("无法打开系统安装界面，请重试"); }
                });
            } catch (Exception ignored) { ready = null; call.reject("更新包校验失败或已失效，请重新下载", "INVALID_PACKAGE"); }
        });
    }

    @Override
    protected void handleOnDestroy() {
        cancelled.set(true);
        if (connection != null) connection.disconnect();
        worker.shutdownNow();
        super.handleOnDestroy();
    }
}
