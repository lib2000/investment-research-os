export type PortfolioResponse = {
  status: string;
  broker: string;
  synced_from: string;
  holdings_count: number;
  summary: Record<string, unknown>;
  holdings: Array<Record<string, unknown>>;
};

export type PaginatedResponse<TItem, TKey extends string> = {
  status: string;
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
  has_next: boolean;
  has_previous: boolean;
} & Record<TKey, TItem[]>;

export type JournalDraft = {
  id: number;
  broker: string;
  source_type: string;
  ticker?: string;
  name?: string;
  draft_status: string;
  updated_at: string;
  payload?: Record<string, unknown>;
};

export type JournalEntryCreateInput = {
  draft_id: number;
  strategy_name?: string;
  setup_tags?: string[];
  entry_reason?: string;
  exit_reason?: string;
  rule_followed?: boolean | null;
  good_points?: string;
  improvement_points?: string;
  memo?: string;
  manual_profit_loss_amount?: number | null;
  manual_profit_rate?: number | null;
  manual_buy_amount?: number | null;
  manual_sell_amount?: number | null;
  planned_entry_price?: number | null;
  actual_entry_price?: number | null;
  stop_loss_price?: number | null;
  target_price?: number | null;
  exit_price?: number | null;
  planned_risk_amount?: number | null;
  realized_r_multiple?: number | null;
};

export type JournalEntryMutationResponse = {
  status: string;
  entry: Record<string, unknown>;
};

export type JournalEntry = {
  id: number;
  draft_id: number;
  broker: string;
  ticker?: string;
  name?: string;
  strategy_name?: string;
  setup_tags?: string[];
  entry_reason?: string;
  exit_reason?: string;
  rule_followed?: boolean | null;
  good_points?: string;
  improvement_points?: string;
  memo?: string;
  manual_profit_loss_amount?: number | null;
  updated_at?: string;
};

export type JournalEntryDeleteResponse = {
  status: string;
  deleted_entry_id: number;
  draft_id: number;
};

export type ManualTransaction = {
  id: number;
  trade_date: string;
  broker: string;
  account_name: string;
  transaction_type: string;
  ticker?: string;
  name?: string;
  currency: string;
  profit_loss_amount_krw?: number;
  dividend_amount_krw?: number;
  tax_amount_krw?: number;
  commission_amount_krw?: number;
};

export type ManualTransactionCreateInput = {
  trade_date: string;
  broker?: string;
  account_name?: string;
  transaction_type?: string;
  ticker?: string;
  name?: string;
  quantity?: number | null;
  price?: number | null;
  buy_amount?: number | null;
  sell_amount?: number | null;
  profit_loss_amount?: number | null;
  dividend_amount?: number | null;
  tax_amount?: number | null;
  commission_amount?: number | null;
  currency?: string;
  fx_rate_krw?: number | null;
  split_adjustment_ratio?: number;
  adjustment_note?: string;
  memo?: string;
};

export type ManualTransactionMutationResponse = {
  status: string;
  transaction: ManualTransaction;
};

export type ManualTransactionsImportError = {
  row?: number;
  message?: string;
};

export type ManualTransactionsImportResponse = {
  status: string;
  file_name: string;
  total_rows: number;
  imported_count: number;
  failed_count: number;
  skipped_count: number;
  transactions: ManualTransaction[];
  errors: ManualTransactionsImportError[];
};

export type ManualTransactionDeleteResponse = {
  status: string;
  deleted_transaction_id: number;
};

export type JournalAnalyticsFilter = {
  startDate?: string;
  endDate?: string;
};

export type JournalAnalyticsResponse = {
  status: string;
  filter_start_date?: string | null;
  filter_end_date?: string | null;
  total_entries: number;
  realized_profit_loss_total: number;
  win_rate: number | null;
  annual_profit: Array<Record<string, unknown>>;
  quarterly_profit: Array<Record<string, unknown>>;
  monthly_profit: Array<Record<string, unknown>>;
  profit_trend: Array<Record<string, unknown>>;
  ticker_allocation: Array<Record<string, unknown>>;
  type_allocation: Array<Record<string, unknown>>;
  account_allocation: Array<Record<string, unknown>>;
  dividend_total: number;
  dividend_by_year: Array<Record<string, unknown>>;
  tax_total: number;
  tax_by_year: Array<Record<string, unknown>>;
  commission_total: number;
  commission_by_year: Array<Record<string, unknown>>;
};
