import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { apiDelete, apiGet, apiPost } from "../api/client";
import type {
  JournalAnalyticsResponse,
  JournalAnalyticsFilter,
  JournalDraft,
  JournalEntry,
  JournalEntryCreateInput,
  JournalEntryDeleteResponse,
  JournalEntryMutationResponse,
  ManualTransaction,
  ManualTransactionCreateInput,
  ManualTransactionDeleteResponse,
  ManualTransactionMutationResponse,
  PaginatedResponse,
  PortfolioResponse,
} from "../api/types";

export function usePortfolio() {
  return useQuery({
    queryKey: ["portfolio"],
    queryFn: () => apiGet<PortfolioResponse>("/api/v1/portfolio"),
    staleTime: 30_000,
  });
}

export function useJournalDrafts(page = 1, pageSize = 20) {
  return useQuery({
    queryKey: ["journal-drafts", page, pageSize],
    queryFn: () =>
      apiGet<PaginatedResponse<JournalDraft, "drafts">>(
        `/api/v1/journal/drafts?page=${page}&page_size=${pageSize}`,
      ),
    staleTime: 15_000,
  });
}

export function useJournalEntries(page = 1, pageSize = 20) {
  return useQuery({
    queryKey: ["journal-entries", page, pageSize],
    queryFn: () =>
      apiGet<PaginatedResponse<JournalEntry, "entries">>(
        `/api/v1/journal/entries?page=${page}&page_size=${pageSize}`,
      ),
    staleTime: 15_000,
  });
}

export function useManualTransactions(page = 1, pageSize = 20) {
  return useQuery({
    queryKey: ["manual-transactions", page, pageSize],
    queryFn: () =>
      apiGet<PaginatedResponse<ManualTransaction, "transactions">>(
        `/api/v1/manual-transactions?page=${page}&page_size=${pageSize}`,
      ),
    staleTime: 15_000,
  });
}

export function useJournalAnalytics(filter: JournalAnalyticsFilter = {}) {
  const query = new URLSearchParams();
  if (filter.startDate) query.set("start_date", filter.startDate);
  if (filter.endDate) query.set("end_date", filter.endDate);
  const suffix = query.toString();

  return useQuery({
    queryKey: ["journal-analytics", filter.startDate ?? null, filter.endDate ?? null],
    queryFn: () =>
      apiGet<JournalAnalyticsResponse>(
        `/api/v1/journal/analytics${suffix ? `?${suffix}` : ""}`,
      ),
    staleTime: 60_000,
  });
}

export function useCreateManualTransaction() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload: ManualTransactionCreateInput) =>
      apiPost<ManualTransactionMutationResponse>("/api/v1/manual-transactions", payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["manual-transactions"] });
      queryClient.invalidateQueries({ queryKey: ["journal-analytics"] });
    },
  });
}

export function useDeleteManualTransaction() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (transactionId: number) =>
      apiDelete<ManualTransactionDeleteResponse>(
        `/api/v1/manual-transactions/${transactionId}`,
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["manual-transactions"] });
      queryClient.invalidateQueries({ queryKey: ["journal-analytics"] });
    },
  });
}

export function useCreateJournalEntry() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload: JournalEntryCreateInput) =>
      apiPost<JournalEntryMutationResponse>("/api/v1/journal/entries", payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["journal-drafts"] });
      queryClient.invalidateQueries({ queryKey: ["journal-entries"] });
      queryClient.invalidateQueries({ queryKey: ["journal-analytics"] });
    },
  });
}

export function useDeleteJournalEntry() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (entryId: number) =>
      apiDelete<JournalEntryDeleteResponse>(`/api/v1/journal/entries/${entryId}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["journal-drafts"] });
      queryClient.invalidateQueries({ queryKey: ["journal-entries"] });
      queryClient.invalidateQueries({ queryKey: ["journal-analytics"] });
    },
  });
}
