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
import { LabelPairedChartLineCaptionRegularIcon } from '@deriv/quill-icons/LabelPaired';
import { DerivLightEmptyCardboardBoxIcon } from '@deriv/quill-icons/Illustration';
import ThemedScrollbars from '../shared_ui/themed-scrollbars';
import { buildLearningPayload, fetchAgentAnalysisWithChart } from '@/services/agent-analysis-api';

import './ai-summary.scss';

const MarkdownContent = ({ content }: { content: string }) => (
  <div className="ai-summary__markdown-body">
    <ReactMarkdown
      components={{
        p: ({ children }) => <p className="ai-summary__markdown-p">{children}</p>,
        ul: ({ children }) => <ul className="ai-summary__markdown-ul">{children}</ul>,
        ol: ({ children }) => <ol className="ai-summary__markdown-ol">{children}</ol>,
        li: ({ children }) => <li className="ai-summary__markdown-li">{children}</li>,
        strong: ({ children }) => <strong className="ai-summary__markdown-strong">{children}</strong>,
        em: ({ children }) => <em className="ai-summary__markdown-em">{children}</em>,
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

const getContractId = (data: TContractInfo) =>
  String(data.transaction_ids?.buy ?? data.contract_id ?? 'unknown');

const AiSummary = observer(({ is_drawer_open = false, variant = 'tutorials', onRunBotClick }: TAiSummary) => {
  const { transactions, run_panel, client, ai_summary } = useStore();
  const { isDesktop } = useDevice();
  const is_compact = variant === 'run-panel';
  const [loading, setLoading] = useState(false);

  React.useEffect(() => {
    if (client?.loginid) ai_summary.restore();
  }, [client?.loginid, ai_summary]);

  const { selected_contract_id, result, error } = ai_summary;

  const transaction_list = transactions.transactions ?? [];
  const contract_trxs = transaction_list.filter(
    (t) => t.type === transaction_elements.CONTRACT && typeof t.data === 'object'
  ) as { type: string; data: TContractInfo }[];

  const selected_contract = contract_trxs.find((t) => getContractId(t.data) === selected_contract_id)?.data ?? null;

  const recent_outcomes = contract_trxs
    .map((t) => (Number(t.data.profit) > 0 ? ('win' as const) : ('loss' as const)))
    .reverse();

  const onAnalyse = async () => {
    if (!selected_contract) return;
    setLoading(true);
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
    }
  };

  const has_trades = contract_trxs.length > 0;

  return (
    <div
      className={classnames('ai-summary', `ai-summary--${variant}`, {
        'run-panel-tab__content': is_compact && isDesktop,
        'run-panel-tab__content--mobile': is_compact && !isDesktop && is_drawer_open,
        'ai-summary--has-result': !!result && !!selected_contract,
        'ai-summary--empty': !has_trades,
      })}
    >
      <div className="ai-summary__header">
        <Text as="p" size="xxs" color="less-prominent">
          <Localize i18n_default_text="Select a trade to get Analyst + Tutor explanations." />
        </Text>
      </div>

      <div className="ai-summary__trades">
        {has_trades && (
          <Text as="p" size="xxs" weight="bold" className="ai-summary__label">
            <Localize i18n_default_text="Past trades" />
          </Text>
        )}
        <ThemedScrollbars className="ai-summary__scrollbar">
          {has_trades ? (
            <div className="ai-summary__list">
              {contract_trxs.map(({ data }) => {
                const profit = Number(data.profit);
                const is_profit = profit >= 0;
                return (
                  <button
                    key={data.transaction_ids?.buy ?? data.contract_id}
                    type="button"
                    className={classnames('ai-summary__trade-item', {
                      'ai-summary__trade-item--selected': selected_contract_id === getContractId(data),
                      'ai-summary__trade-item--profit': is_profit,
                      'ai-summary__trade-item--loss': !is_profit,
                    })}
                    onClick={() => ai_summary.setSelectedContractId(getContractId(data))}
                  >
                    <LabelPairedChartLineCaptionRegularIcon
                      className="ai-summary__trade-icon"
                      height="16px"
                      width="16px"
                      fill="var(--text-general)"
                    />
                    <span className="ai-summary__trade-type">{data.contract_type}</span>
                    <span
                      className={classnames('ai-summary__trade-pnl', {
                        'ai-summary__trade-pnl--profit': is_profit,
                        'ai-summary__trade-pnl--loss': !is_profit,
                      })}
                    >
                      {is_profit ? '+' : ''}
                      {data.profit} {data.currency}
                    </span>
                  </button>
                );
              })}
            </div>
          ) : (
            <div className="ai-summary__empty">
              <DerivLightEmptyCardboardBoxIcon
                className="ai-summary__empty-icon"
                height="80px"
                width="80px"
              />
              <Text as="p" size="xs" color="less-prominent" className="ai-summary__empty-text">
                <Localize i18n_default_text="No transactions yet. Run the bot to see your trades and get AI-powered explanations." />
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
        </ThemedScrollbars>
      </div>

      {has_trades && (
        <div className="ai-summary__actions">
          <Button
            id="ai-summary__analyse-btn"
            text={loading ? localize('Analysing...') : localize('Get AI Analysis')}
            onClick={onAnalyse}
            disabled={!selected_contract || loading}
            primary
          />
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

      {result && selected_contract && (
        <ThemedScrollbars className="ai-summary__result">
          <div className="ai-summary__result-content">
            <div className="ai-summary__result-card ai-summary__result-card--analyst">
              <Text as="p" size="xs" weight="bold" className="ai-summary__result-card-title">
                <span className="ai-summary__result-card-title-icon">📊</span>{' '}
                <Localize i18n_default_text="Analyst" />
              </Text>
              <div className="ai-summary__markdown ai-summary__recommendation">
                <MarkdownContent content={result.learning_recommendation} />
              </div>
            </div>
            <div className="ai-summary__result-card ai-summary__result-card--tutor">
              <Text as="p" size="xs" weight="bold" className="ai-summary__result-card-title">
                <span className="ai-summary__result-card-title-icon">📚</span>{' '}
                <Localize i18n_default_text="Tutor" />
              </Text>
              <div className="ai-summary__markdown ai-summary__explanation">
                <MarkdownContent content={result.trade_explanation} />
              </div>
            </div>
            {result.learning_points?.length > 0 && (
              <div className="ai-summary__result-card ai-summary__result-card--learning">
                <Text as="p" size="xs" weight="bold" className="ai-summary__result-card-title">
                  <span className="ai-summary__result-card-title-icon">💡</span>{' '}
                  <Localize i18n_default_text="Learning points" />
                </Text>
                <div className="ai-summary__markdown ai-summary__points-wrapper">
                  <MarkdownContent content={result.learning_points.map((p) => `- ${p}`).join('\n')} />
                </div>
              </div>
            )}
          </div>
        </ThemedScrollbars>
      )}
    </div>
  );
});

export default AiSummary;
