import { useCallback, useEffect, useState } from 'react';
import { clearCSRFToken, isDerivThirdPartyAuth, validateCSRFToken } from '@/components/shared/utils/config/config';
import { clearAuthData } from '@/utils/auth-utils';

/** Single account from Deriv third-party OAuth redirect (acctN, tokenN, curN) */
export interface DerivOAuthAccount {
    account: string;
    token: string;
    currency: string;
}

/**
 * OAuth callback parameters extracted from URL
 */
export interface OAuthCallbackParams {
    code: string | null;
    state: string | null;
    error: string | null;
    error_description: string | null;
    /** Set when third-party OAuth redirect was parsed (acct1, token1, ...) */
    derivOAuthAccounts?: DerivOAuthAccount[];
}

/**
 * OAuth callback processing result
 */
export interface OAuthCallbackResult {
    isProcessing: boolean;
    isValid: boolean;
    params: OAuthCallbackParams;
    error: string | null;
    cleanupURL: () => void;
    /** True when third-party OAuth redirect was handled (tokens stored, no code exchange) */
    isThirdPartySuccess: boolean;
}

/**
 * Custom hook to handle OAuth callback flow
 *
 * This hook:
 * 1. Extracts OAuth parameters (code, state, error) from URL
 * 2. Validates CSRF token (state parameter)
 * 3. Returns the authorization code and a cleanup function
 *
 * Note: Call cleanupURL() after you've processed the authorization code
 *
 * @returns OAuth callback processing result with cleanupURL function
 *
 * @example
 * ```tsx
 * const { isProcessing, isValid, params, error, cleanupURL } = useOAuthCallback();
 *
 * useEffect(() => {
 *   if (!isProcessing && isValid && params.code) {
 *     // Exchange code for tokens
 *     exchangeCodeForTokens(params.code).then(() => {
 *       cleanupURL(); // Clean up after processing
 *     });
 *   }
 * }, [isProcessing, isValid, params.code]);
 * ```
 */
/** Parse Deriv third-party redirect params (acct1, token1, cur1, acct2, ...) into account list */
function parseDerivOAuthRedirectParams(urlParams: URLSearchParams): DerivOAuthAccount[] {
    const accounts: DerivOAuthAccount[] = [];
    let n = 1;
    while (true) {
        const acct = urlParams.get(`acct${n}`);
        const token = urlParams.get(`token${n}`);
        const cur = urlParams.get(`cur${n}`);
        if (!acct || !token) break;
        accounts.push({
            account: acct,
            token,
            currency: cur || 'usd',
        });
        n += 1;
    }
    return accounts;
}

/** Remove Deriv third-party params from URL (acctN, tokenN, curN) */
function cleanupThirdPartyParams(url: URL): void {
    const keysToDelete: string[] = [];
    url.searchParams.forEach((_, key) => {
        if (/^acct\d+$/.test(key) || /^token\d+$/.test(key) || /^cur\d+$/.test(key)) {
            keysToDelete.push(key);
        }
    });
    keysToDelete.forEach(k => url.searchParams.delete(k));
}

export const useOAuthCallback = (): OAuthCallbackResult => {
    const [result, setResult] = useState<
        Omit<OAuthCallbackResult, 'cleanupURL' | 'isThirdPartySuccess'> & { isThirdPartySuccess: boolean }
    >({
        isProcessing: true,
        isValid: false,
        isThirdPartySuccess: false,
        params: {
            code: null,
            state: null,
            error: null,
            error_description: null,
        },
        error: null,
    });

    // Cleanup function that can be called by the consuming component
    const cleanupURL = useCallback(() => {
        const url = new URL(window.location.href);
        url.searchParams.delete('code');
        url.searchParams.delete('state');
        url.searchParams.delete('scope');
        url.searchParams.delete('error');
        url.searchParams.delete('error_description');
        cleanupThirdPartyParams(url);
        window.history.replaceState({}, '', url.toString());
    }, []);

    useEffect(() => {
        const urlParams = new URLSearchParams(window.location.search);

        // Third-party OAuth (Deriv): redirect has acct1, token1, cur1, ...
        if (isDerivThirdPartyAuth()) {
            const acct1 = urlParams.get('acct1');
            const token1 = urlParams.get('token1');
            if (acct1 && token1) {
                const accounts = parseDerivOAuthRedirectParams(urlParams);
                if (accounts.length > 0) {
                    const first = accounts[0];
                    sessionStorage.setItem('deriv_oauth_token', first.token);
                    // Store in shape existing app expects (deriv_accounts: { account_id, currency }; active_loginid)
                    const derivAccountsShape = accounts.map(a => ({
                        account_id: a.account,
                        currency: a.currency,
                    }));
                    sessionStorage.setItem('deriv_accounts', JSON.stringify(derivAccountsShape));
                    localStorage.setItem('active_loginid', first.account);
                    const isDemo = first.account.startsWith('VRT') || first.account.startsWith('VRTC');
                    localStorage.setItem('account_type', isDemo ? 'demo' : 'real');
                    setResult({
                        isProcessing: false,
                        isValid: true,
                        isThirdPartySuccess: true,
                        params: {
                            code: null,
                            state: null,
                            error: null,
                            error_description: null,
                            derivOAuthAccounts: accounts,
                        },
                        error: null,
                    });
                    cleanupURL();
                }
                return;
            }
        }

        // Extract OAuth parameters (dbot/internal flow)
        const code = urlParams.get('code');
        const state = urlParams.get('state');
        const error = urlParams.get('error');
        const error_description = urlParams.get('error_description');

        // Check if this is an OAuth callback (has code or error parameter)
        const isOAuthCallback = code !== null || error !== null || state !== null;

        if (!isOAuthCallback) {
            // Not an OAuth callback, mark as complete
            setResult({
                isProcessing: false,
                isValid: false,
                isThirdPartySuccess: false,
                params: { code: null, state: null, error: null, error_description: null },
                error: null,
            });
            return;
        }

        // Handle OAuth error response
        if (error) {
            console.error('OAuth error:', error, error_description);
            setResult({
                isProcessing: false,
                isValid: false,
                isThirdPartySuccess: false,
                params: { code, state, error, error_description },
                error: error_description || error,
            });

            cleanupURL();
            return;
        }

        // Validate CSRF token (state parameter) - dbot flow only
        if (!state) {
            console.error('[DEBUG] Missing state parameter in OAuth callback');
            clearAuthData();
            setResult({
                isProcessing: false,
                isValid: false,
                isThirdPartySuccess: false,
                params: { code, state, error, error_description },
                error: 'Missing state parameter - potential security threat',
            });

            window.location.replace(window.location.origin);
            return;
        }

        if (!validateCSRFToken(state)) {
            console.error('[DEBUG] CSRF token validation failed - potential security threat');
            clearAuthData();
            setResult({
                isProcessing: false,
                isValid: false,
                isThirdPartySuccess: false,
                params: { code, state, error, error_description },
                error: 'CSRF token validation failed',
            });
            return;
        }

        // CSRF validation passed
        clearCSRFToken();

        // Validate that we have the authorization code
        if (!code) {
            console.error('Missing authorization code in OAuth callback');
            setResult({
                isProcessing: false,
                isValid: false,
                isThirdPartySuccess: false,
                params: { code, state, error, error_description },
                error: 'Missing authorization code',
            });

            cleanupURL();
            return;
        }

        setResult({
            isProcessing: false,
            isValid: true,
            isThirdPartySuccess: false,
            params: { code, state, error, error_description },
            error: null,
        });
    }, [cleanupURL]); // Run only once on mount

    return {
        ...result,
        cleanupURL,
        isThirdPartySuccess: result.isThirdPartySuccess,
    };
};
