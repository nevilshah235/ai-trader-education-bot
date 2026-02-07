import React, { useState } from 'react';
import { observer } from 'mobx-react-lite';
import classnames from 'classnames';
import ReactMarkdown from 'react-markdown';
import Button from '@/components/shared_ui/button';
import Text from '@/components/shared_ui/text';
import { TContractInfo } from '@/components/summary/summary-card.types';
import { transaction_elements } from '@/constants/transactions';
import { useStore } from '@/hooks/useStore';
import { Localize, localize } from '@deriv-com/translations';
import { useDevice } from '@deriv-com/ui';
import { LabelPairedChevronDownLgRegularIcon, LabelPairedChevronUpLgRegularIcon } from '@deriv/quill-icons/LabelPaired';
import { DerivLightEmptyCardboardBoxIcon } from '@deriv/quill-icons/Illustration';
import ThemedScrollbars from '../shared_ui/themed-scrollbars';
import {
  buildLearningPayload,
  fetchAgentAnalysisWithChart,
  fetchLearnFromTrade,
} from '@/services/agent-analysis-api';

import './ai-summary.scss';

const getContractId = (data: TContractInfo) =>
  String(data.transaction_ids?.buy ?? data.contract_id ?? 'unknown');

const toTimestamp = (val?: string | number): number | null => {
  if (val == null || val === '') return null;
  if (typeof val === 'number') return val < 1e12 ? val * 1000 : val;
  const t = new Date(val).getTime();
  return isNaN(t) ? null : t;
};

const formatDuration = (contract: TContractInfo | null): string => {
  if (!contract) return '—';
  let start: number | null = null;
  let end: number | null = null;
  if (contract.entry_tick_time != null && contract.exit_tick_time != null) {
    start = toTimestamp(contract.entry_tick_time);
    end = toTimestamp(contract.exit_tick_time);
  }
  if ((start == null || end == null) && contract.date_start != null && (contract as { date_expiry?: string | number }).date_expiry != null) {
    start = toTimestamp(contract.date_start);
    end = toTimestamp((contract as { date_expiry?: string | number }).date_expiry);
  }
  if (start == null || end == null) return '—';
  const sec = Math.round((end - start) / 1000);
  if (sec < 60) return sec + 's';
  if (sec < 3600) return Math.floor(sec / 60) + 'm';
  if (sec < 86400) return (sec / 3600).toFixed(1) + 'h';
  return Math.floor(sec / 86400) + 'd';
};

const MiniSparkline = ({
  entry,
  exit,
  isProfit,
}: {
  entry: number;
  exit: number;
  isProfit: boolean;
}) => {
  const min = Math.min(entry, exit);
  const max = Math.max(entry, exit);
  const range = max - min || 1;
  const entryNorm = (entry - min) / range;
  const exitNorm = (exit - min) / range;
  const entryY = 100 - entryNorm * 100;
  const exitY = 100 - exitNorm * 100;
  const points = '0,' + entryY + ' 50,' + exitY + ' 100,' + exitY;
  const entryStr = entry.toFixed(2);
  const exitStr = exit.toFixed(2);
  return (
    <div className="ai-summary__sparkline-container">
      <div className="ai-summary__sparkline-labels">
        <span className="ai-summary__sparkline-label" title={localize('Price at contract start')}>
          📍 Entry: {entryStr}
        </span>
        <span className="ai-summary__sparkline-label" title={localize('Price at contract end')}>
          🏁 Exit: {exitStr}
        </span>
      </div>
      <svg viewBox="0 0 100 100" preserveAspectRatio="none" className="ai-summary__sparkline">
        <polyline
          points={points}
          fill="none"
          stroke={isProfit ? 'var(--purchase-main-1, #4bb4b3)' : 'var(--purchase-main-2, #ff444f)'}
          strokeWidth="2"
        />
      </svg>
    </div>
  );
};

const CollapsibleCard = ({
  title,
  content,
  defaultOpen = false,
  children,
}: {
  title: string;
  content?: React.ReactNode;
  defaultOpen?: boolean;
  children?: React.ReactNode;
}) => {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className={classnames('ai-summary__insight-card', { 'ai-summary__insight-card--open': open })}>
      <button
        type="button"
        className="ai-summary__insight-card-header"
        onClick={() => setOpen(!open)}
      >
        <span className="ai-summary__insight-card-title">{title}</span>
        {open ? (
          <LabelPairedChevronUpLgRegularIcon height="16px" width="16px" fill="var(--text-general)" />
        ) : (
          <LabelPairedChevronDownLgRegularIcon height="16px" width="16px" fill="var(--text-general)" />
        )}
      </button>
      {open && (
        <div className="ai-summary__insight-card-content">
          {content || children}
        </div>
      )}
    </div>
  );
};

const MarkdownContent = ({ content }: { content: string }) => (
  <div className="ai-summary__markdown-body">
    <ReactMarkdown
      components={{
        p: ({ children }) => <p className="ai-summary__markdown-p">{children}</p>,
        ul: ({ children }) => <ul className="ai-summary__markdown-ul">{children}</ul>,
        ol: ({ children }) => <ol className="ai-summary__markdown-ol">{children}</ol>,
        li: ({ children }) => <li className="ai-summary__markdown-li">{children}</li>,
        strong: ({ children }) => <strong>{children}</strong>,
        em: ({ children }) => <em>{children}</em>,
      }}
    >
      {content}
    </ReactMarkdown>
  </div>
);

type TAiSummary = {
  is_drawer_open?: boolean;
  variant?: 'run-panel' | 'tutorials';
  onRunBotClick?: () => void;
};

const AiSummary = observer(({ is_drawer_open = false, variant = 'tutorials', onRunBotClick }: TAiSummary) => {
  const { transactions, run_panel, client, ai_summary } = useStore();
  const { isDesktop } = useDevice();
  const is_compact = variant === 'run-panel';
  const [loading, setLoading] = useState(false);
  const [loadingAction, setLoadingAction] = useState<'analyse' | 'learn' | null>(null);
  const [showWhatIf, setShowWhatIf] = useState(false);

  const { selected_contract_id, result, error } = ai_summary;

  const transaction_list = transactions.transactions ?? [];
  const contract_trxs = transaction_list.filter(
    (t) => t.type === transaction_elements.CONTRACT && typeof t.data === 'object'
  ) as { type: string; data: TContractInfo }[];

  const selected_contract = contract_trxs.find((t) => getContractId(t.data) === selected_contract_id)?.data ?? null;

  const recent_outcomes = contract_trxs
    .map((t) => (Number(t.data.profit) > 0 ? ('win' as const) : ('loss' as const)))
    .reverse();

  React.useEffect(() => {
    if (client?.loginid) ai_summary.restore();
  }, [client?.loginid, ai_summary]);

  React.useEffect(() => {
    if (contract_trxs.length > 0 && !selected_contract_id) {
      ai_summary.setSelectedContractId(getContractId(contract_trxs[contract_trxs.length - 1].data));
    }
  }, [contract_trxs, selected_contract_id, ai_summary]);

  const onAnalyse = async () => {
    if (!selected_contract) return;
    setLoading(true);
    setLoadingAction('analyse');
    ai_summary.setError(null);
    ai_summary.setResult(null);
    try {
      const payload = buildLearningPayload(
        selected_contract,
        run_panel.run_id,
        contract_trxs.findIndex((t) => t.data === selected_contract) + 1,
        recent_outcomes
      );
      const res = await fetchAgentAnalysisWithChart(payload, {
        loginid: client?.loginid || undefined,
      });
      ai_summary.setResult(res);
    } catch (e) {
      ai_summary.setError(e instanceof Error ? e.message : 'Failed to get AI analysis');
    } finally {
      setLoading(false);
      setLoadingAction(null);
    }
  };

  const onLearnFromTrade = async () => {
    if (!selected_contract) return;
    setLoading(true);
    setLoadingAction('learn');
    ai_summary.setError(null);
    ai_summary.setResult(null);
    try {
      const payload = buildLearningPayload(
        selected_contract,
        run_panel.run_id,
        contract_trxs.findIndex((t) => t.data === selected_contract) + 1,
        recent_outcomes
      );
      const res = await fetchLearnFromTrade(payload, client?.loginid || undefined);
      ai_summary.setResult(res);
    } catch (e) {
      ai_summary.setError(e instanceof Error ? e.message : 'Failed to get RAG learning');
    } finally {
      setLoading(false);
      setLoadingAction(null);
    }
  };

  const has_trades = contract_trxs.length > 0;
  const has_result = !!result && !!selected_contract;
  const is_profit = selected_contract ? Number(selected_contract.profit) >= 0 : false;

  const entryVal = parseFloat(String(selected_contract?.entry_tick ?? selected_contract?.buy_price ?? 0)) || 0;
  const exitVal = parseFloat(String(selected_contract?.exit_tick ?? selected_contract?.payout ?? 0)) || entryVal;

  return (
    <div
      className={classnames('ai-summary', 'ai-summary--' + variant, {
        'run-panel-tab__content': is_compact && isDesktop,
        'run-panel-tab__content--mobile': is_compact && !isDesktop && is_drawer_open,
        'ai-summary--has-result': has_result,
        'ai-summary--empty': !has_trades,
      })}
    >
      {has_trades ? (
        <>
          <aside className="ai-summary__sidebar">
            <div className="ai-summary__sidebar-label">
              📜 <Localize i18n_default_text="Recent trades" />
            </div>
            <ThemedScrollbars className="ai-summary__sidebar-scroll">
              <ul className="ai-summary__trade-list">
                {contract_trxs.map(({ data }) => {
                  const profit = Number(data.profit);
                  const win = profit >= 0;
                  const isSelected = selected_contract_id === getContractId(data);
                  return (
                    <li key={getContractId(data)}>
                      <button
                        type="button"
                        className={classnames('ai-summary__trade-btn', {
                          'ai-summary__trade-btn--selected': isSelected,
                          'ai-summary__trade-btn--win': win,
                          'ai-summary__trade-btn--loss': !win,
                        })}
                        onClick={() => ai_summary.setSelectedContractId(getContractId(data))}
                      >
                        <span className="ai-summary__trade-direction">{data.contract_type}</span>
                        <span className="ai-summary__trade-outcome">{win ? 'Win' : 'Loss'}</span>
                        <span
                          className={classnames('ai-summary__trade-pnl', {
                            'ai-summary__trade-pnl--win': win,
                            'ai-summary__trade-pnl--loss': !win,
                          })}
                        >
                          {win ? '+' : ''}
                          {data.profit} {data.currency}
                        </span>
                      </button>
                    </li>
                  );
                })}
              </ul>
            </ThemedScrollbars>
            <div className="ai-summary__sidebar-actions">
              <Button
                id="ai-summary__analyse-btn"
                text={
                  loading && loadingAction === 'analyse'
                    ? localize('Analysing...')
                    : localize('Analyse')
                }
                onClick={onAnalyse}
                disabled={!selected_contract || loading}
                primary
              />
              <Button
                id="ai-summary__learn-btn"
                text={
                  loading && loadingAction === 'learn'
                    ? localize('Learning...')
                    : localize('Learn from trade')
                }
                onClick={onLearnFromTrade}
                disabled={!selected_contract || loading}
                secondary
              />
            </div>
          </aside>

          {!has_result ? (
            <div className="ai-summary__placeholder">
              <Text as="p" size="xs" color="less-prominent">
                <Localize i18n_default_text="Select a trade and click Analyse to view post-trade breakdown." />
              </Text>
            </div>
          ) : (
            <div className="ai-summary__content-area">
              <section className="ai-summary__outcome">
                <div className="ai-summary__sparkline-wrap">
                  <MiniSparkline entry={entryVal} exit={exitVal} isProfit={is_profit} />
                </div>
                <h2
                  className={classnames('ai-summary__outcome-header', {
                    'ai-summary__outcome-header--win': is_profit,
                    'ai-summary__outcome-header--loss': !is_profit,
                  })}
                >
                  <Localize i18n_default_text="Trade Result" />: {is_profit ? '✅ Win' : '❌ Loss'}
                </h2>
                <div className="ai-summary__metrics">
                  <div className="ai-summary__metric">
                    <span className="ai-summary__metric-label" title={localize('Price at contract start')}>
                      📍 <Localize i18n_default_text="Entry" />
                    </span>
                    <span className="ai-summary__metric-value">
                      {selected_contract?.entry_tick ?? selected_contract?.buy_price ?? '—'}
                    </span>
                  </div>
                  <div className="ai-summary__metric">
                    <span className="ai-summary__metric-label" title={localize('Price at contract end')}>
                      🏁 <Localize i18n_default_text="Exit" />
                    </span>
                    <span className="ai-summary__metric-value">
                      {selected_contract?.exit_tick ?? selected_contract?.payout ?? '—'}
                    </span>
                  </div>
                  <div className="ai-summary__metric">
                    <span className="ai-summary__metric-label" title={localize('How long the trade was active')}>
                      ⏱️ <Localize i18n_default_text="Duration" />
                    </span>
                    <span className="ai-summary__metric-value">
                      {formatDuration(selected_contract ?? null)}
                    </span>
                  </div>
                  <div className="ai-summary__metric">
                    <span className="ai-summary__metric-label">
                      🎯 <Localize i18n_default_text="Direction" />
                    </span>
                    <span className="ai-summary__metric-value">
                      {selected_contract?.contract_type ?? '—'}
                    </span>
                  </div>
                </div>
              </section>

              <aside className="ai-summary__insights">
                <CollapsibleCard
                  title={'📋 ' + localize('What Happened')}
                  defaultOpen
                  content={<MarkdownContent content={result!.learning_recommendation} />}
                />
                <CollapsibleCard
                  title={'💡 ' + localize('Why This Matters')}
                  defaultOpen={false}
                  content={<MarkdownContent content={result!.trade_explanation} />}
                />
                {result!.learning_points?.length > 0 && (
                  <CollapsibleCard
                    title={'🎯 ' + localize('What This Says About Your Trading')}
                    defaultOpen={false}
                    content={
                      <MarkdownContent
                        content={result!.learning_points.map((p) => '- ' + p).join('\n')}
                      />
                    }
                  />
                )}
                <div className="ai-summary__whatif">
                  <button
                    type="button"
                    className={classnames('ai-summary__whatif-toggle', {
                      'ai-summary__whatif-toggle--active': showWhatIf,
                    })}
                    onClick={() => setShowWhatIf(!showWhatIf)}
                  >
🕐 <Localize i18n_default_text="If duration were longer…" />
                  </button>
                  {showWhatIf && (
                    <p className="ai-summary__whatif-placeholder">
                      <Localize i18n_default_text="Longer durations typically reduce the impact of short-term noise. Consider testing with 1–5 minute contracts." />
                    </p>
                  )}
                </div>
              </aside>
            </div>
          )}
        </>
      ) : (
        <div className="ai-summary__empty">
          <DerivLightEmptyCardboardBoxIcon className="ai-summary__empty-icon" height="64px" width="64px" />
          <Text as="p" size="xs" color="less-prominent" className="ai-summary__empty-text">
            <Localize i18n_default_text="No completed trades. Run the bot to analyse outcomes." />
          </Text>
          {onRunBotClick && (
            <Button
              className="ai-summary__empty-cta"
              text={localize('Run the bot')}
              onClick={onRunBotClick}
              primary
            />
          )}
        </div>
      )}

      {error && (
        <div className="ai-summary__error">
          <Text as="p" size="xs" color="loss-danger">
            {error}
          </Text>
          <Button
            className="ai-summary__error-retry"
            text={localize('Retry')}
            onClick={() => {
              ai_summary.setError(null);
              onAnalyse();
            }}
            secondary
            small
          />
        </div>
      )}
    </div>
  );
});

export default AiSummary;
