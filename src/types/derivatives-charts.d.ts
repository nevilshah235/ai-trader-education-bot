declare module '@deriv-com/derivatives-charts' {
    import { ComponentType, ReactNode } from 'react';

    export interface SmartChartProps {
        id?: string;
        barriers?: any[];
        showLastDigitStats?: boolean;
        chartControlsWidgets?: any;
        enabledChartFooter?: boolean;
        stateChangeListener?: (state: string, option?: any) => void;
        chartStatusListener?: (status: boolean) => void;
        toolbarWidget?: () => ReactNode;
        chartType?: string;
        isMobile?: boolean;
        enabledNavigationWidget?: boolean;
        granularity?: number;
        requestAPI?: (req: any) => Promise<any>;
        requestForget?: () => void;
        requestForgetStream?: () => void;
        requestSubscribe?: (req: any, callback: (data: any) => void) => Promise<void>;
        settings?: {
            assetInformation?: boolean;
            countdown?: boolean;
            isHighestLowestMarkerEnabled?: boolean;
            language?: string;
            position?: string;
            theme?: string;
        };
        symbol?: string;
        topWidgets?: () => ReactNode;
        isConnectionOpened?: boolean;
        getMarketsOrder?: (symbols: any[]) => string[];
        isLive?: boolean;
        leftMargin?: number;
    }

    export interface ChartTitleProps {
        onChange?: (symbol: string) => void;
        enabled?: boolean;
        open_market?: {
            category?: string;
            subcategory?: string;
            market?: string;
        };
        isNestedList?: boolean;
    }

    export interface ToolbarWidgetProps {
        position?: 'top' | 'bottom';
        children?: ReactNode;
    }

    export const SmartChart: ComponentType<SmartChartProps>;
    export const ChartTitle: ComponentType<ChartTitleProps>;
    export const ChartMode: ComponentType<any>;
    export const DrawTools: ComponentType<any>;
    export const Share: ComponentType<any>;
    export const StudyLegend: ComponentType<any>;
    export const ToolbarWidget: ComponentType<ToolbarWidgetProps>;
    export const Views: ComponentType<any>;
    export const setSmartChartsPublicPath: (path: string) => void;
}
