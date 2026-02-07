/**
 * Hidden SmartCharts instance used to capture chart image with entry/exit and P/L
 * when a trade completes or when user requests AI analysis.
 */

import React, { useEffect, useRef, useState } from 'react';
import { observer } from 'mobx-react-lite';
import { SmartChart, TGranularity, TStateChangeListener } from '@deriv-com/smartcharts-champion';

import { useSmartChartAdaptor } from '@/hooks/useSmartChartAdaptor';
import { useStore } from '@/hooks/useStore';
import { captureChartWithOverlay, dataUrlToBase64 } from '@/utils/chart-capture';

import '@deriv-com/smartcharts-champion/dist/smartcharts.css';

function toEpoch(value: string | number | undefined): number | undefined {
    if (value === undefined || value === null) return undefined;
    if (typeof value === 'number') return value > 1e12 ? Math.floor(value / 1000) : value;
    const d = new Date(value);
    return isNaN(d.getTime()) ? undefined : Math.floor(d.getTime() / 1000);
}

const CAPTURE_WIDTH = 800;
const CAPTURE_HEIGHT = 400;

const AnalysisChartCapture = observer(() => {
    const { chart_capture, chart_store, common, ui } = useStore();
    const { getMarketsOrder } = chart_store;
    const { chartData, getQuotes, subscribeQuotes, unsubscribeQuotes } = useSmartChartAdaptor();
    const containerRef = useRef<HTMLDivElement>(null);
    const [chartReady, setChartReady] = useState(false);
    const captureTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

    const request = chart_capture.pendingRequest;
    const contract = request?.contract;
    const symbol = request?.symbol;

    const settings = {
        assetInformation: false,
        countdown: false,
        isHighestLowestMarkerEnabled: false,
        language: common.current_language?.toLowerCase() ?? 'en',
        position: 'bottom' as const,
        theme: ui.is_dark_mode_on ? 'dark' : 'light',
    };

    const handleStateChange: TStateChangeListener = (state) => {
        if (state === 'READY') {
            setChartReady(true);
        }
    };

    useEffect(() => {
        if (!request || !containerRef.current || !contract) return;

        setChartReady(false);

        const doCapture = () => {
            if (!containerRef.current || !contract) {
                chart_capture.rejectCapture(new Error('Chart container or contract missing'));
                return;
            }
            captureChartWithOverlay(containerRef.current, contract)
                .then(dataUrl => {
                    const base64 = dataUrlToBase64(dataUrl);
                    chart_capture.resolveCapture(base64);
                })
                .catch(err => {
                    chart_capture.rejectCapture(err instanceof Error ? err : new Error(String(err)));
                });
        };

        if (chartReady) {
            // Small delay so chart has finished painting
            captureTimeoutRef.current = setTimeout(doCapture, 500);
        }

        return () => {
            if (captureTimeoutRef.current) {
                clearTimeout(captureTimeoutRef.current);
                captureTimeoutRef.current = null;
            }
        };
    }, [chartReady, request, contract, chart_capture]);

    if (!request || !symbol || chartData.activeSymbols.length === 0) {
        return null;
    }

    const startEpoch = toEpoch(contract?.date_start);
    const endEpoch = toEpoch(
        (contract as Record<string, unknown>)?.date_expiry ?? contract?.date_start
    );

    return (
        <div
            style={{
                position: 'fixed',
                left: -CAPTURE_WIDTH - 100,
                top: 0,
                width: CAPTURE_WIDTH,
                height: CAPTURE_HEIGHT,
                zIndex: -1,
                visibility: 'hidden',
                pointerEvents: 'none',
            }}
            ref={containerRef}
            dir='ltr'
        >
            <SmartChart
                id='dbot-analysis-capture'
                key={`analysis-capture-${symbol}-${contract?.contract_id ?? 'unknown'}`}
                symbol={symbol}
                granularity={0 as TGranularity}
                chartType='line'
                barriers={[]}
                showLastDigitStats={false}
                chartControlsWidgets={null}
                enabledChartFooter={false}
                stateChangeListener={handleStateChange}
                toolbarWidget={() => null}
                getQuotes={getQuotes}
                subscribeQuotes={subscribeQuotes}
                unsubscribeQuotes={unsubscribeQuotes}
                chartData={{
                    activeSymbols: chartData.activeSymbols,
                    tradingTimes: chartData.tradingTimes,
                }}
                settings={settings}
                startEpoch={startEpoch}
                endEpoch={endEpoch}
                scrollToEpoch={startEpoch ?? undefined}
                contractInfo={contract ?? undefined}
                shouldDrawTicksFromContractInfo={!!contract}
                isLive={false}
                leftMargin={80}
                isConnectionOpened={true}
                getMarketsOrder={getMarketsOrder}
            />
        </div>
    );
});

export default AnalysisChartCapture;
