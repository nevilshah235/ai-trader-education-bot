/**
 * Chart capture: html2canvas + P/L overlay for analyst.
 */

import html2canvas from 'html2canvas';

import type { TContractInfo } from '@/components/summary/summary-card.types';

/**
 * Draw P/L caption and optional entry/exit labels on a canvas (e.g. after chart screenshot).
 */
export function drawChartOverlay(
    canvas: HTMLCanvasElement,
    contract: TContractInfo
): void {
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const profit = Number(contract.profit) ?? 0;
    const currency = contract.currency ?? 'USD';
    const isWin = profit >= 0;
    const plText = `P/L: ${isWin ? '+' : ''}${profit.toFixed(2)} ${currency}`;

    const padding = 12;
    const fontSize = 14;
    const x = canvas.width - padding - 120;
    const y = padding + fontSize;

    ctx.font = `bold ${fontSize}px sans-serif`;
    ctx.textBaseline = 'top';
    ctx.fillStyle = isWin ? 'rgba(0, 160, 80, 0.95)' : 'rgba(255, 60, 60, 0.95)';
    ctx.fillRect(x - 4, y - 2, 116, fontSize + 6);
    ctx.fillStyle = '#fff';
    ctx.fillText(plText, x, y);
}

/**
 * Capture an element (chart container) as PNG and draw P/L overlay.
 * Returns base64 data URL (including "data:image/png;base64," prefix).
 */
export async function captureChartWithOverlay(
    element: HTMLElement,
    contract: TContractInfo
): Promise<string> {
    const canvas = await html2canvas(element, {
        useCORS: true,
        allowTaint: true,
        scale: 1,
        logging: false,
    });
    drawChartOverlay(canvas, contract);
    return canvas.toDataURL('image/png');
}

/**
 * Extract base64 payload from a data URL (strip "data:image/png;base64,").
 */
export function dataUrlToBase64(dataUrl: string): string {
    const i = dataUrl.indexOf(',');
    return i >= 0 ? dataUrl.slice(i + 1) : dataUrl;
}
