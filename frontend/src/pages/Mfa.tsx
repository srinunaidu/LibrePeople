import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Layout } from '@/components/Layout';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/inputs';
import api, { errorMessage } from '@/lib/api';

export default function MfaPage() {
  const [status, setStatus] = useState<{ mfa_enabled: boolean; mfa_enrolled_at?: string } | null>(null);
  const [loading, setLoading] = useState(false);
  const [enrolling, setEnrolling] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const [disabling, setDisabling] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [provisioningUri, setProvisioningUri] = useState<string | null>(null);
  const [provisioningSecret, setProvisioningSecret] = useState<string | null>(null);
  const [qrCodeDataUri, setQrCodeDataUri] = useState<string | null>(null);
  const [recoveryCodes, setRecoveryCodes] = useState<string[] | null>(null);
  const [totpCode, setTotpCode] = useState('');
  const [password, setPassword] = useState('');

  const fetchStatus = async () => {
    try {
      const res = await api.get('/auth/mfa/status');
      setStatus(res.data);
    } catch (err: any) {
      setError(errorMessage(err, 'Failed to load MFA status'));
    }
  };

  useEffect(() => {
    fetchStatus();
  }, []);

  const handleEnroll = async () => {
    setEnrolling(true);
    setError(null);
    try {
      const res = await api.post('/auth/mfa/enroll');
      setProvisioningUri(res.data.provisioning_uri);
      setRecoveryCodes(res.data.recovery_codes);
      // The server renders the QR so the TOTP secret is never sent to a
      // third-party image service.
      setQrCodeDataUri(res.data.qr_code_data_uri ?? null);
      // Extract secret from provisioning URI
      const parsed = new URL(res.data.provisioning_uri);
      const secret = parsed.searchParams.get('secret');
      if (secret) setProvisioningSecret(secret);
      setEnrolling(false);
    } catch (err: any) {
      setError(errorMessage(err, 'Enrollment failed'));
    } finally {
      setEnrolling(false);
    }
  };

  const handleConfirm = async () => {
    setConfirming(true);
    setError(null);
    try {
      await api.post('/auth/mfa/confirm', { totp_code: totpCode });
      setStatus({ mfa_enabled: true, mfa_enrolled_at: new Date().toISOString() });
      setTotpCode('');
    } catch (err: any) {
      setError(errorMessage(err, 'Confirmation failed'));
    } finally {
      setConfirming(false);
    }
  };

  const handleDisable = async () => {
    setDisabling(true);
    setError(null);
    try {
      await api.post('/auth/mfa/disable', { password });
      setStatus({ mfa_enabled: false, mfa_enrolled_at: undefined });
      setPassword('');
    } catch (err: any) {
      setError(errorMessage(err, 'Disable failed'));
    } finally {
      setDisabling(false);
    }
  };

  return (
    <Layout>
    <div className="p-8 max-w-2xl">
      <div className="mb-6">
        <h1 className="text-[var(--font-size-2xl)] font-bold text-fg">Multi-Factor Authentication</h1>
        <p className="text-text-secondary">
          Add an extra layer of security to your account with two-factor authentication.
        </p>
      </div>

      <div className="card p-6">
        <h2 className="text-[var(--font-size-lg)] font-bold text-fg mb-4">Current Status</h2>
        <div className="flex items-center gap-4 mb-4">
          <Badge variant={status?.mfa_enabled ? "green" : "rose"} size="md">
            {status?.mfa_enabled ? 'Enabled' : 'Disabled'}
          </Badge>
        </div>
        {status?.mfa_enrolled_at && (
          <p className="text-sm text-text-secondary">
            Enabled: {new Date(status.mfa_enrolled_at).toLocaleDateString()}
          </p>
        )}
      </div>

      {status?.mfa_enabled ? (
        <div className="card p-6">
          <h2 className="text-[var(--font-size-lg)] font-bold text-fg mb-4">Manage MFA</h2>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-fg mb-2">
                Current Password
              </label>
              <Input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Enter your current password"
              />
            </div>
            <Button
              onClick={handleDisable}
              disabled={disabling || !password}
              className="w-full"
              variant="danger"
            >
              {disabling ? 'Disabling...' : 'Disable MFA'}
            </Button>
          </div>
        </div>
      ) : (
        <div className="card p-6">
          <h2 className="text-[var(--font-size-lg)] font-bold text-fg mb-4">Enable MFA</h2>
          <p className="text-sm text-text-secondary mb-4">
            Set up two-factor authentication using an authenticator app (e.g., Google Authenticator, Authy).
          </p>

          {!provisioningUri ? (
            <Button onClick={handleEnroll} disabled={enrolling} className="w-full">
              {enrolling ? 'Setting up...' : 'Enable MFA'}
            </Button>
          ) : (
            <>
              <div className="bg-surface-inset border border-border rounded-lg p-6 mb-4">
                <h3 className="text-sm font-bold text-fg mb-2">Scan this QR code:</h3>
                <div className="flex items-center gap-4 mb-4">
                  {qrCodeDataUri ? (
                    <img
                      src={qrCodeDataUri}
                      alt="QR code for the authenticator app"
                      className="w-32 h-32 bg-surface p-2 border border-border"
                    />
                  ) : (
                    <p className="text-sm text-text-secondary">
                      The QR code could not be loaded. Enter the secret key by hand.
                    </p>
                  )}
                  <div className="flex flex-col">
                    <p className="text-sm text-text-secondary mb-2">Secret key:</p>
                    <code className="text-xs font-mono break-all bg-surface-inset p-2 border border-border">
                      {provisioningSecret}
                    </code>
                  </div>
                </div>
                <div className="space-y-2">
                  <h3 className="text-sm font-bold text-fg mb-2">Recovery Codes</h3>
                  <p className="text-sm text-text-secondary mb-2">
                    Save these codes somewhere safe. You can use them to sign in if you lose access to your authenticator app.
                    <strong className="text-fg"> The server shows them once, on this screen — there is no way to view them again.</strong>
                  </p>
                  <div className="flex flex-wrap gap-2">
                    {recoveryCodes?.map((code, i) => (
                      <span key={i} className="px-2 py-1 rounded border border-border text-sm bg-surface-inset">
                        {code}
                      </span>
                    ))}
                  </div>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => {
                      const text = (recoveryCodes || []).join('\n');
                      void navigator.clipboard?.writeText(text);
                    }}
                    disabled={!recoveryCodes?.length}
                  >
                    Copy codes
                  </Button>
                </div>
              </div>
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-fg mb-2">
                    Verification Code
                  </label>
                  <Input
                    type="text"
                    value={totpCode}
                    onChange={(e) => setTotpCode(e.target.value)}
                    placeholder="6-digit code"
                    maxLength={6}
                  />
                </div>
                <Button onClick={handleConfirm} disabled={confirming || totpCode.length !== 6} className="w-full">
                  {confirming ? 'Verifying...' : 'Verify & Enable'}
                </Button>
              </div>
            </>
          )}
        </div>
      )}

      {error && <div className="mt-4 p-3 rounded bg-[var(--semantic-status-error-light)] text-[var(--semantic-status-error)] text-sm">{error}</div>}
    </div>
    </Layout>
  );
}