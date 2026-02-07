import React, { useState } from 'react';
import { observer } from 'mobx-react-lite';
import classnames from 'classnames';
import Button from '@/components/shared_ui/button';
import Text from '@/components/shared_ui/text';
import { TContractInfo } from '@/components/summary/summary-card.types';
import { transaction_elements } from '@/constants/transactions';
import { useStore } from '@/hooks/useStore';
import { Localize, localize } from '@deriv-com/translations';
import { useDevice } from '@deriv-com/ui';
import ThemedScrollbars from '../shared_ui/themed-scrollbars';
import {
  buildLearningPayload,
  fetchAgentAnalysis,
  type AgentAnalysisResponse,
} from '@/services/agent-analysis-api';

import './ai-summary.scss';

type TAiSummary = {
  is_drawer_open: boolean;
};

const AiSummary = observer(({ is_drawer_open }: TAiSummary) => {
  const { transactions, run_panel } = useStore();
  const { isDesktop } = useDevice();
  const [selected_contract, setSelectedContract] = useState<TContractInfo | null>(null);
  const [result, setResult] = useState<AgentAnalysisResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const transaction_list = transactions.transactions ?? [];
  const contract_trxs = transaction_list.filter(
    (t) => t.type === transaction_elements.CONTRACT && typeof t.data === 'object'
  ) as { type: string; data: TContractInfo }[];

  const recent_outcomes = contract_trxs
    .map((t) => (Number(t.data.profit) > 0 ? ('win' as const) : ('loss' as const)))
    .reverse();

  const onAnalyse = async () => {
    if (!selected_contract) return;
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const payload = buildLearningPayload(
        selected_contract,
        run_panel.run_id,
        contract_trxs.findIndex((t) => t.data === selected_contract) + 1,
        recent_outcomes
      );
      const res = await fetchAgentAnalysis(payload);
      setResult(res);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to get AI analysis');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      className={classnames('ai-summary', {
        'run-panel-tab__content': isDesktop,
        'run-panel-tab__content--mobile': !isDesktop && is_drawer_open,
      })}
    >
      <div className="ai-summary__header">
        <Text as="p" size="xs" weight="bold">
          <Localize i18n_default_text="AI Summary" />
        </Text>
        <Text as="p" size="xxs" color="less-prominent">
          <Localize i18n_default_text="Select a trade to get Analyst + Tutor explanations." />
        </Text>
      </div>

      <div className="ai-summary__trades">
        <Text as="p" size="xxs" weight="bold" className="ai-summary__label">
          <Localize i18n_default_text="Past trades" />
        </Text>
        <ThemedScrollbars className="ai-summary__scrollbar">
          {contract_trxs.length ? (
            <div className="ai-summary__list">
              {contract_trxs.map(({ data }) => (
                <button
                  key={data.transaction_ids?.buy ?? data.contract_id}
                  type="button"
                  className={classnames('ai-summary__trade-item', {
                    'ai-summary__trade-item--selected': selected_contract === data,
                  })}
                  onClick={() => {
                    setSelectedContract(data);
                    setResult(null);
                    setError(null);
                  }}
                >
                  <span className="ai-summary__trade-type">{data.contract_type}</span>
                  <span className="ai-summary__trade-pnl">
                    {Number(data.profit) >= 0 ? '+' : ''}
                    {data.profit} {data.currency}
                  </span>
                </button>
              ))}
            </div>
          ) : (
            <Text as="p" size="xxs" color="less-prominent">
              <Localize i18n_default_text="No transactions yet. Run the bot to see trades." />
            </Text>
          )}
        </ThemedScrollbars>
      </div>

      <div className="ai-summary__actions">
        <Button
          id="ai-summary__analyse-btn"
          text={loading ? localize('Analysing...') : localize('Get AI Analysis')}
          onClick={onAnalyse}
          disabled={!selected_contract || loading}
          primary
        />
      </div>

      {error && (
        <div className="ai-summary__error">
          <Text as="p" size="xs" color="loss-danger">
            {error}
          </Text>
        </div>
      )}

      {result && (
        <ThemedScrollbars className="ai-summary__result">
          <div className="ai-summary__result-content">
            <Text as="p" size="xxs" weight="bold">
              <Localize i18n_default_text="Analyst" />
            </Text>
            <Text as="p" size="xxs" className="ai-summary__recommendation">
              {result.learning_recommendation}
            </Text>
            <Text as="p" size="xxs" weight="bold" className="ai-summary__label">
              <Localize i18n_default_text="Tutor" />
            </Text>
            <Text as="p" size="xxs" className="ai-summary__explanation">
              {result.trade_explanation}
            </Text>
            {result.learning_points?.length > 0 && (
              <>
                <Text as="p" size="xxs" weight="bold" className="ai-summary__label">
                  <Localize i18n_default_text="Learning points" />
                </Text>
                <ul className="ai-summary__points">
                  {result.learning_points.map((pt, i) => (
                    <li key={i}>
                      <Text as="span" size="xxs">
                        {pt}
                      </Text>
                    </li>
                  ))}
                </ul>
              </>
            )}
          </div>
        </ThemedScrollbars>
      )}
    </div>
  );
});

export default AiSummary;
