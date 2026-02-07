/**
 * Sync transaction data to backend DB for AI analyst agents.
 * Best-effort, fire-and-forget; session storage remains source of truth for UI.
 */

import type { TContractInfo } from '@/components/summary/summary-card.types';

const BACKEND_BASE =
    process.env.AGENT_ANALYSIS_API_URL || (typeof window !== 'undefined' ? '' : 'http://localhost:8000');

function toIsoDate(value: string | number | undefined): string {
    if (!value) return new Date().toISOString();
    if (typeof value === 'number') return new Date(value * 1000).toISOString();
    const d = new Date(value);
    return isNaN(d.getTime()) ? new Date().toISOString() : d.toISOString();
}

/** Payload for POST /api/transactions (single transaction). */
export function buildTransactionPayload(
    contract: TContractInfo,
    loginid: string,
    run_id?: string,
    chart_image_b64?: string | null
): Record<string, unknown> {
    const buy = contract.transaction_ids?.buy ?? contract.contract_id;
    const payload: Record<string, unknown> = {
        loginid,
        contract_id: String(buy ?? contract.contract_id ?? 'unknown'),
        run_id: run_id ?? contract.run_id ?? undefined,
        buy_price: Number(contract.buy_price) || 0,
        payout: Number(contract.payout) || Number(contract.bid_price) || 0,
        profit: Number(contract.profit) || 0,
        currency: contract.currency || 'USD',
        contract_type: contract.contract_type || 'CALL',
        shortcode: contract.shortcode || 'N/A',
        date_start: toIsoDate(contract.date_start ?? contract.purchase_time),
        date_expiry: toIsoDate((contract as Record<string, unknown>).date_expiry ?? contract.date_start),
        entry_tick: String(contract.entry_tick ?? contract.entry_spot ?? ''),
        exit_tick: String(contract.exit_tick ?? (contract as Record<string, unknown>).exit_spot ?? ''),
    };
    if (chart_image_b64 != null && chart_image_b64 !== '') {
        payload.chart_image_b64 = chart_image_b64;
    }
    return payload;
}

/**
 * POST a single transaction to the backend. Fire-and-forget; logs errors.
 * When chart_image_b64 is provided (e.g. from capture at trade completion), it is stored with the transaction.
 */
export function syncTransactionToBackend(
    contract: TContractInfo,
    loginid: string,
    run_id?: string,
    chart_image_b64?: string | null
): void {
    if (!loginid) return;
    const url = `${BACKEND_BASE}/api/transactions`;
    const body = buildTransactionPayload(contract, loginid, run_id, chart_image_b64);
    fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
    }).catch(err => {
        if (typeof console !== 'undefined' && console.warn) {
            console.warn('[transaction-sync] Failed to sync transaction:', err);
        }
    });
}
