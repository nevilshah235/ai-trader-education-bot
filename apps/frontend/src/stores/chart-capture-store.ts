/**
 * Store for chart capture requests. Used when a trade completes or when user
 * requests AI analysis and we need to capture the SmartCharts image with
 * entry/exit and P/L overlay.
 */

import { action, makeObservable, observable } from 'mobx';

import type { TContractInfo } from '@/components/summary/summary-card.types';

export type ChartCaptureRequest = {
    contract: TContractInfo;
    symbol: string;
};

type ResolveReject = {
    resolve: (value: string) => void;
    reject: (reason: Error) => void;
};

export default class ChartCaptureStore {
    /** Current capture request; when set, AnalysisChartCapture should render and capture. */
    pendingRequest: ChartCaptureRequest | null = null;

    private resolvers: ResolveReject | null = null;

    constructor() {
        makeObservable(this, {
            pendingRequest: observable,
            requestCapture: action,
            resolveCapture: action,
            rejectCapture: action,
            clearRequest: action,
        });
    }

    /**
     * Request a chart capture for the given contract and symbol.
     * Returns a promise that resolves with base64 PNG when capture is done.
     */
    requestCapture(contract: TContractInfo, symbol: string): Promise<string> {
        return new Promise((resolve, reject) => {
            this.pendingRequest = { contract, symbol };
            this.resolvers = { resolve, reject };
        });
    }

    resolveCapture(base64: string): void {
        if (this.resolvers) {
            this.resolvers.resolve(base64);
            this.resolvers = null;
        }
        this.pendingRequest = null;
    }

    rejectCapture(err: Error): void {
        if (this.resolvers) {
            this.resolvers.reject(err);
            this.resolvers = null;
        }
        this.pendingRequest = null;
    }

    clearRequest(): void {
        if (this.resolvers) {
            this.resolvers.reject(new Error('Chart capture cancelled'));
            this.resolvers = null;
        }
        this.pendingRequest = null;
    }
}
