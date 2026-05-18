import { StatusBar } from "expo-status-bar";
import { useCallback, useEffect, useMemo, useState } from "react";
import {
  ActivityIndicator,
  Pressable,
  SafeAreaView,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from "react-native";

import {
  API_BASE_URL,
  fetchJournalDrafts,
  fetchLatestSync,
  fetchPortfolio,
  syncKiwoomData,
} from "./api";

const ACCESS_TOKEN =
  process.env.EXPO_PUBLIC_DEV_ACCESS_TOKEN || "dev-local-token";

const TABS = [
  { id: "portfolio", label: "포트폴리오" },
  { id: "sync", label: "동기화" },
  { id: "drafts", label: "일지 초안" },
];

export default function App() {
  const [activeTab, setActiveTab] = useState("portfolio");
  const [loading, setLoading] = useState(false);
  const [portfolio, setPortfolio] = useState(null);
  const [latestSync, setLatestSync] = useState(null);
  const [drafts, setDrafts] = useState([]);
  const [lastError, setLastError] = useState("");

  const loadDashboard = useCallback(async () => {
    setLoading(true);
    setLastError("");
    try {
      const [portfolioResult, syncResult, draftResult] = await Promise.all([
        fetchPortfolio(ACCESS_TOKEN),
        fetchLatestSync(ACCESS_TOKEN),
        fetchJournalDrafts(ACCESS_TOKEN),
      ]);

      setPortfolio(portfolioResult);
      setLatestSync(syncResult?.sync_run || null);
      setDrafts(draftResult?.drafts || []);
    } catch (error) {
      setLastError(error.message);
    } finally {
      setLoading(false);
    }
  }, []);

  const runSync = useCallback(async () => {
    setLoading(true);
    setLastError("");
    try {
      await syncKiwoomData(ACCESS_TOKEN);
      await loadDashboard();
      setActiveTab("drafts");
    } catch (error) {
      setLastError(error.message);
    } finally {
      setLoading(false);
    }
  }, [loadDashboard]);

  useEffect(() => {
    loadDashboard();
  }, [loadDashboard]);

  const content = useMemo(() => {
    if (activeTab === "portfolio") {
      return <PortfolioView portfolio={portfolio} />;
    }
    if (activeTab === "sync") {
      return <SyncView latestSync={latestSync} onSync={runSync} loading={loading} />;
    }
    return <DraftsView drafts={drafts} />;
  }, [activeTab, drafts, latestSync, loading, portfolio, runSync]);

  return (
    <SafeAreaView style={styles.safeArea}>
      <StatusBar style="dark" />
      <View style={styles.header}>
        <View>
          <Text style={styles.title}>InvestLog</Text>
          <Text style={styles.subtitle}>KIWOOM · {API_BASE_URL}</Text>
        </View>
        {loading ? <ActivityIndicator color="#0f766e" /> : null}
      </View>

      <View style={styles.tabs}>
        {TABS.map((tab) => (
          <Pressable
            key={tab.id}
            onPress={() => setActiveTab(tab.id)}
            style={[
              styles.tabButton,
              activeTab === tab.id ? styles.tabButtonActive : null,
            ]}
          >
            <Text
              style={[
                styles.tabText,
                activeTab === tab.id ? styles.tabTextActive : null,
              ]}
            >
              {tab.label}
            </Text>
          </Pressable>
        ))}
      </View>

      {lastError ? <Text style={styles.errorText}>{lastError}</Text> : null}

      <ScrollView contentContainerStyle={styles.content}>{content}</ScrollView>
    </SafeAreaView>
  );
}

function PortfolioView({ portfolio }) {
  const summary = portfolio?.summary || {};
  const holdings = portfolio?.holdings || [];

  return (
    <View style={styles.stack}>
      <View style={styles.panel}>
        <Text style={styles.panelTitle}>자산 요약</Text>
        <View style={styles.metricGrid}>
          <Metric label="평가금액" value={formatKrw(summary.total_evaluation_amount)} />
          <Metric label="매입금액" value={formatKrw(summary.total_purchase_amount)} />
          <Metric
            label="평가손익"
            value={formatKrw(summary.total_evaluation_profit_loss)}
            tone={summary.total_evaluation_profit_loss < 0 ? "danger" : "good"}
          />
          <Metric
            label="수익률"
            value={formatPercent(summary.total_profit_rate)}
            tone={summary.total_profit_rate < 0 ? "danger" : "good"}
          />
        </View>
      </View>

      <View style={styles.panel}>
        <View style={styles.rowBetween}>
          <Text style={styles.panelTitle}>보유 종목</Text>
          <Text style={styles.countText}>{portfolio?.holdings_count || 0}</Text>
        </View>
        {holdings.map((holding) => (
          <HoldingRow key={holding.ticker || holding.name} holding={holding} />
        ))}
        {!holdings.length ? <Text style={styles.emptyText}>보유 종목이 없습니다.</Text> : null}
      </View>
    </View>
  );
}

function SyncView({ latestSync, onSync, loading }) {
  return (
    <View style={styles.stack}>
      <View style={styles.panel}>
        <Text style={styles.panelTitle}>최근 동기화</Text>
        <Text style={styles.syncStatus}>{latestSync?.status || "기록 없음"}</Text>
        <Text style={styles.mutedText}>
          {latestSync?.finished_at ? formatDateTime(latestSync.finished_at) : "아직 저장된 동기화가 없습니다."}
        </Text>
        <View style={styles.syncGrid}>
          <Metric label="보유종목" value={String(latestSync?.portfolio_holdings_count || 0)} />
          <Metric label="일지 초안" value={String(latestSync?.needs_review_count || 0)} />
        </View>
      </View>

      <Pressable
        onPress={onSync}
        disabled={loading}
        style={[styles.primaryButton, loading ? styles.primaryButtonDisabled : null]}
      >
        <Text style={styles.primaryButtonText}>
          {loading ? "동기화 중" : "키움 데이터 동기화"}
        </Text>
      </Pressable>
    </View>
  );
}

function DraftsView({ drafts }) {
  return (
    <View style={styles.stack}>
      <View style={styles.panel}>
        <View style={styles.rowBetween}>
          <Text style={styles.panelTitle}>복기 대기</Text>
          <Text style={styles.countText}>{drafts.length}</Text>
        </View>
        {drafts.map((draft) => (
          <DraftRow key={draft.id} draft={draft} />
        ))}
        {!drafts.length ? <Text style={styles.emptyText}>복기할 초안이 없습니다.</Text> : null}
      </View>
    </View>
  );
}

function Metric({ label, value, tone }) {
  return (
    <View style={styles.metric}>
      <Text style={styles.metricLabel}>{label}</Text>
      <Text
        style={[
          styles.metricValue,
          tone === "danger" ? styles.dangerText : null,
          tone === "good" ? styles.goodText : null,
        ]}
      >
        {value}
      </Text>
    </View>
  );
}

function HoldingRow({ holding }) {
  return (
    <View style={styles.listRow}>
      <View style={styles.listMain}>
        <Text style={styles.itemName}>{holding.name || holding.ticker}</Text>
        <Text style={styles.mutedText}>
          {holding.ticker} · {holding.quantity || 0}주 · 평균 {formatKrw(holding.average_price)}
        </Text>
      </View>
      <View style={styles.listSide}>
        <Text
          style={[
            styles.sideValue,
            holding.evaluation_profit_loss < 0 ? styles.dangerText : styles.goodText,
          ]}
        >
          {formatPercent(holding.profit_rate)}
        </Text>
        <Text style={styles.mutedText}>{formatKrw(holding.evaluation_amount)}</Text>
      </View>
    </View>
  );
}

function DraftRow({ draft }) {
  const payload = draft.payload || {};
  const title = draft.name || payload.name || draft.ticker || "미분류";

  return (
    <View style={styles.listRow}>
      <View style={styles.listMain}>
        <Text style={styles.itemName}>{title}</Text>
        <Text style={styles.mutedText}>
          {draft.source_type} · {draft.draft_status}
        </Text>
      </View>
      <View style={styles.listSide}>
        <Text style={styles.sideValue}>{draft.ticker || payload.ticker || "-"}</Text>
        <Text style={styles.mutedText}>{formatDateTime(draft.updated_at)}</Text>
      </View>
    </View>
  );
}

function formatKrw(value) {
  if (value === null || value === undefined) {
    return "-";
  }
  return `${Number(value).toLocaleString("ko-KR")}원`;
}

function formatPercent(value) {
  if (value === null || value === undefined) {
    return "-";
  }
  return `${Number(value).toFixed(2)}%`;
}

function formatDateTime(value) {
  if (!value) {
    return "-";
  }
  return new Date(value).toLocaleString("ko-KR", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

const styles = StyleSheet.create({
  safeArea: {
    flex: 1,
    backgroundColor: "#f5f7fb",
  },
  header: {
    alignItems: "center",
    flexDirection: "row",
    justifyContent: "space-between",
    paddingHorizontal: 20,
    paddingTop: 16,
    paddingBottom: 12,
  },
  title: {
    color: "#111827",
    fontSize: 28,
    fontWeight: "800",
  },
  subtitle: {
    color: "#64748b",
    fontSize: 12,
    marginTop: 4,
  },
  tabs: {
    backgroundColor: "#e5eaf1",
    borderRadius: 8,
    flexDirection: "row",
    marginHorizontal: 20,
    padding: 4,
  },
  tabButton: {
    alignItems: "center",
    borderRadius: 6,
    flex: 1,
    minHeight: 40,
    justifyContent: "center",
  },
  tabButtonActive: {
    backgroundColor: "#ffffff",
  },
  tabText: {
    color: "#64748b",
    fontSize: 13,
    fontWeight: "700",
  },
  tabTextActive: {
    color: "#0f172a",
  },
  content: {
    padding: 20,
    paddingBottom: 40,
  },
  stack: {
    gap: 14,
  },
  panel: {
    backgroundColor: "#ffffff",
    borderColor: "#dbe3ef",
    borderRadius: 8,
    borderWidth: 1,
    padding: 16,
  },
  panelTitle: {
    color: "#111827",
    fontSize: 17,
    fontWeight: "800",
    marginBottom: 12,
  },
  metricGrid: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 10,
  },
  syncGrid: {
    flexDirection: "row",
    gap: 10,
    marginTop: 14,
  },
  metric: {
    backgroundColor: "#f8fafc",
    borderColor: "#e2e8f0",
    borderRadius: 8,
    borderWidth: 1,
    flexBasis: "47%",
    flexGrow: 1,
    minHeight: 72,
    padding: 12,
  },
  metricLabel: {
    color: "#64748b",
    fontSize: 12,
    fontWeight: "700",
  },
  metricValue: {
    color: "#111827",
    fontSize: 17,
    fontWeight: "800",
    marginTop: 8,
  },
  rowBetween: {
    alignItems: "center",
    flexDirection: "row",
    justifyContent: "space-between",
  },
  countText: {
    color: "#0f766e",
    fontSize: 18,
    fontWeight: "800",
  },
  listRow: {
    borderTopColor: "#e5e7eb",
    borderTopWidth: 1,
    flexDirection: "row",
    gap: 12,
    justifyContent: "space-between",
    paddingVertical: 12,
  },
  listMain: {
    flex: 1,
    minWidth: 0,
  },
  listSide: {
    alignItems: "flex-end",
    maxWidth: 120,
  },
  itemName: {
    color: "#111827",
    fontSize: 15,
    fontWeight: "800",
  },
  sideValue: {
    color: "#111827",
    fontSize: 14,
    fontWeight: "800",
  },
  mutedText: {
    color: "#64748b",
    fontSize: 12,
    marginTop: 4,
  },
  syncStatus: {
    color: "#0f766e",
    fontSize: 22,
    fontWeight: "800",
    textTransform: "uppercase",
  },
  primaryButton: {
    alignItems: "center",
    backgroundColor: "#0f766e",
    borderRadius: 8,
    minHeight: 48,
    justifyContent: "center",
    paddingHorizontal: 16,
  },
  primaryButtonDisabled: {
    backgroundColor: "#94a3b8",
  },
  primaryButtonText: {
    color: "#ffffff",
    fontSize: 15,
    fontWeight: "800",
  },
  errorText: {
    backgroundColor: "#fef2f2",
    borderColor: "#fecaca",
    borderRadius: 8,
    borderWidth: 1,
    color: "#b91c1c",
    fontSize: 13,
    marginHorizontal: 20,
    marginTop: 12,
    padding: 10,
  },
  emptyText: {
    color: "#64748b",
    fontSize: 14,
    paddingVertical: 10,
  },
  dangerText: {
    color: "#dc2626",
  },
  goodText: {
    color: "#0f766e",
  },
});
