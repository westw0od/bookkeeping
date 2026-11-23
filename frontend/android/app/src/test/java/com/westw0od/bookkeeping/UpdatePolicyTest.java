package com.westw0od.bookkeeping;

import org.junit.Test;
import static org.junit.Assert.*;
import java.security.MessageDigest;
import java.nio.charset.StandardCharsets;

public class UpdatePolicyTest {
    private final String hash = "a".repeat(64);

    @Test public void downloadStaysOnSelectedHttpsOrigin() throws Exception {
        assertEquals("https://39.107.13.249/downloads/android/8/" + hash + ".apk",
            UpdatePolicy.downloadUri("https://39.107.13.249", 8, hash, 4000000).toString());
        assertEquals("https://ledger.example:8443/downloads/android/8/" + hash + ".apk",
            UpdatePolicy.downloadUri("https://ledger.example:8443/", 8, hash, 1).toString());
    }
    @Test public void rejectsCredentialsPathsAndUntrustedTransport() throws Exception {
        for (String origin : new String[]{"http://example.com", "https://user:password@example.com", "https://example.com/other", "https://example.com?next=evil", "https://example.com/#x"}) {
            try { UpdatePolicy.downloadUri(origin, 8, hash, 100); fail(origin); }
            catch (IllegalArgumentException expected) { }
        }
    }
    @Test public void boundsPayloadAndRejectsMalformedHash() throws Exception {
        for (long size : new long[]{0, -1, UpdatePolicy.MAX_BYTES + 1}) {
            try { UpdatePolicy.downloadUri("https://example.com", 8, hash, size); fail(); }
            catch (IllegalArgumentException expected) { }
        }
        try { UpdatePolicy.downloadUri("https://example.com", 8, "../private", 100); fail(); }
        catch (IllegalArgumentException expected) { }
    }
    @Test public void detectsHashCorruption() throws Exception {
        byte[] digest = MessageDigest.getInstance("SHA-256").digest("abc".getBytes(StandardCharsets.UTF_8));
        assertTrue(UpdatePolicy.matchesHash(digest, "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"));
        assertFalse(UpdatePolicy.matchesHash(digest, hash));
    }
}
