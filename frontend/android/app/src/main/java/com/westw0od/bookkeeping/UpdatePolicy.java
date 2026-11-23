package com.westw0od.bookkeeping;

import java.net.URI;
import java.security.MessageDigest;

/** Pure validation shared by download and installation, independent of the UI. */
final class UpdatePolicy {
    static final long MAX_BYTES = 100L * 1024 * 1024;

    static URI downloadUri(String origin, int version, String hash, long size) throws Exception {
        URI base = new URI(origin);
        if (!"https".equals(base.getScheme()) || base.getHost() == null || base.getUserInfo() != null ||
            base.getQuery() != null || base.getFragment() != null ||
            !(base.getPath().isEmpty() || "/".equals(base.getPath())) ||
            version <= 0 || hash == null || !hash.matches("[a-f0-9]{64}") || size <= 0 || size > MAX_BYTES) {
            throw new IllegalArgumentException("更新信息不正确，请重新检查更新");
        }
        return base.resolve("/downloads/android/" + version + "/" + hash + ".apk");
    }

    static boolean matchesHash(byte[] digest, String expected) {
        StringBuilder hex = new StringBuilder();
        for (byte value : digest) hex.append(String.format(java.util.Locale.ROOT, "%02x", value & 0xff));
        return MessageDigest.isEqual(hex.toString().getBytes(java.nio.charset.StandardCharsets.US_ASCII),
                expected.getBytes(java.nio.charset.StandardCharsets.US_ASCII));
    }
}
