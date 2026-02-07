import { action, makeObservable, observable } from 'mobx';
import { getStoredItemsByKey, setStoredItemsByKey } from '../utils/session-storage';
import type { AgentAnalysisResponse } from '../services/agent-analysis-api';
import type RootStore from './root-store';

const AI_SUMMARY_CACHE = 'ai_summary_cache';

type TStoredState = {
  selected_contract_id: string | null;
  result: AgentAnalysisResponse | null;
  error: string | null;
};

export default class AiSummaryStore {
  root_store: RootStore;

  selected_contract_id: string | null = null;
  result: AgentAnalysisResponse | null = null;
  error: string | null = null;

  constructor(root_store: RootStore) {
    makeObservable(this, {
      selected_contract_id: observable,
      result: observable,
      error: observable,
      setSelectedContractId: action.bound,
      setResult: action.bound,
      setError: action.bound,
      clear: action.bound,
      restore: action.bound,
      persist: action.bound,
    });
    this.root_store = root_store;
  }

  restore() {
    const loginid = this.root_store.client?.loginid;
    if (!loginid) return;
    const stored = getStoredItemsByKey(AI_SUMMARY_CACHE, {}) as Record<string, TStoredState>;
    const user_state = stored[loginid];
    if (user_state) {
      this.selected_contract_id = user_state.selected_contract_id ?? null;
      this.result = user_state.result ?? null;
      this.error = user_state.error ?? null;
    }
  }

  persist() {
    const loginid = this.root_store.client?.loginid;
    if (!loginid) return;
    const stored = getStoredItemsByKey(AI_SUMMARY_CACHE, {}) as Record<string, TStoredState>;
    stored[loginid] = {
      selected_contract_id: this.selected_contract_id,
      result: this.result,
      error: this.error,
    };
    setStoredItemsByKey(AI_SUMMARY_CACHE, stored);
  }

  setSelectedContractId(id: string | null) {
    this.selected_contract_id = id;
    this.result = null;
    this.error = null;
    this.persist();
  }

  setResult(result: AgentAnalysisResponse | null) {
    this.result = result;
    this.error = null;
    this.persist();
  }

  setError(error: string | null) {
    this.error = error;
    this.persist();
  }

  clear() {
    this.selected_contract_id = null;
    this.result = null;
    this.error = null;
    this.persist();
  }
}
