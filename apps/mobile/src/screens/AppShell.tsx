import { useState } from "react";
import * as DocumentPicker from "expo-document-picker";
import {
  ActivityIndicator,
  type KeyboardTypeOptions,
  Pressable,
  SafeAreaView,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
  useWindowDimensions,
} from "react-native";
import { BarChart, LineChart, PieChart } from "react-native-gifted-charts";

import { apiConfig } from "../api/client";
import {
  useCreateManualTransaction,
  useCreateJournalEntry,
  useDeleteJournalEntry,
  useDeleteManualTransaction,
  useImportManualTransactionsCsv,
  useImportManualTransactionsCsvFile,
  useJournalAnalytics,
  useJournalDrafts,
  useJournalEntries,
  useManualTransactionsCsvTemplate,
  useManualTransactions,
  usePortfolio,
} from "../hooks/useInvestmentQueries";
import type { JournalEntry, ManualTransactionsImportError, RelatedOrderExecution } from "../api/types";

type TabKey = "portfolio" | "drafts" | "entries" | "manual" | "analytics";
type AnalyticsRangeKey = "1m" | "3m" | "6m" | "1y" | "all";
type ProfitBasisKey = "monthly" | "quarterly" | "annual";
type AllocationBasisKey = "ticker" | "type" | "account";

type ManualFormState = {
  tradeDate: string;
  broker: string;
  accountName: string;
  transactionType: string;
  ticker: string;
  name: string;
  quantity: string;
  price: string;
  profitLossAmount: string;
  dividendAmount: string;
  taxAmount: string;
  commissionAmount: string;
  currency: string;
  memo: string;
};

type JournalEntryFormState = {
  draftId: number | null;
  strategyName: string;
  setupTags: string;
  entryReason: string;
  exitReason: string;
  ruleFollowed: "unknown" | "followed" | "broken";
  goodPoints: string;
  improvementPoints: string;
  memo: string;
  profitLossAmount: string;
};

const tabs: Array<{ key: TabKey; label: string }> = [
  { key: "portfolio", label: "포트폴리오" },
  { key: "drafts", label: "일지 초안" },
  { key: "entries", label: "일지" },
  { key: "manual", label: "수동입력" },
  { key: "analytics", label: "분석" },
];

const analyticsRanges: Array<{ key: AnalyticsRangeKey; label: string }> = [
  { key: "1m", label: "1개월" },
  { key: "3m", label: "3개월" },
  { key: "6m", label: "6개월" },
  { key: "1y", label: "1년" },
  { key: "all", label: "전체" },
];

const profitBasisOptions: Array<{ key: ProfitBasisKey; label: string }> = [
  { key: "monthly", label: "월간" },
  { key: "quarterly", label: "분기" },
  { key: "annual", label: "연간" },
];

const allocationBasisOptions: Array<{ key: AllocationBasisKey; label: string }> = [
  { key: "ticker", label: "종목별" },
  { key: "type", label: "유형별" },
  { key: "account", label: "계좌별" },
];

const manualCsvSampleText =
  "거래일,증권사,계좌,유형,종목코드,종목명,수량,가격,매매손익,배당,세금,수수료,통화\n" +
  "2026-05-22,타증권,기타,trade,005930,삼성전자,1,80000,0,0,0,0,KRW";
const apiBaseLabel = apiConfig.baseUrl.replace(/^https?:\/\//, "");

const defaultManualForm = (): ManualFormState => ({
  tradeDate: formatDateParam(new Date()),
  broker: "MANUAL",
  accountName: "기타",
  transactionType: "trade",
  ticker: "",
  name: "",
  quantity: "",
  price: "",
  profitLossAmount: "",
  dividendAmount: "",
  taxAmount: "",
  commissionAmount: "",
  currency: "KRW",
  memo: "",
});

const defaultJournalEntryForm = (): JournalEntryFormState => ({
  draftId: null,
  strategyName: "",
  setupTags: "",
  entryReason: "",
  exitReason: "",
  ruleFollowed: "unknown",
  goodPoints: "",
  improvementPoints: "",
  memo: "",
  profitLossAmount: "",
});

export function AppShell() {
  const [activeTab, setActiveTab] = useState<TabKey>("portfolio");

  return (
    <SafeAreaView style={styles.safeArea}>
      <View style={styles.header}>
        <Text style={styles.title}>InvestLog</Text>
        <Text numberOfLines={1} style={styles.subtitle}>
          {`KIWOOM · ${apiBaseLabel}`}
        </Text>
      </View>
      <View style={styles.tabs}>
        {tabs.map((tab) => (
          <Pressable
            key={tab.key}
            testID={`tab-${tab.key}`}
            onPress={() => setActiveTab(tab.key)}
            style={[styles.tab, activeTab === tab.key && styles.activeTab]}
          >
            <Text style={[styles.tabText, activeTab === tab.key && styles.activeTabText]}>
              {tab.label}
            </Text>
          </Pressable>
        ))}
      </View>
      <ScrollView contentContainerStyle={styles.content}>
        {activeTab === "portfolio" && <PortfolioScreen />}
        {activeTab === "drafts" && <DraftsScreen />}
        {activeTab === "entries" && <JournalEntriesScreen />}
        {activeTab === "manual" && <ManualTransactionsScreen />}
        {activeTab === "analytics" && <AnalyticsScreen />}
      </ScrollView>
    </SafeAreaView>
  );
}

function PortfolioScreen() {
  const portfolio = usePortfolio();

  if (portfolio.isLoading) return <Loading />;
  if (portfolio.isError) return <ErrorText message={portfolio.error.message} />;

  const data = portfolio.data;
  return (
    <View style={styles.panel}>
      <Text style={styles.panelTitle}>포트폴리오</Text>
      <Metric label="보유 종목" value={`${data?.holdings_count ?? 0}개`} />
      <Metric label="증권사" value={data?.broker ?? "-"} />
      <Metric label="동기화" value={data?.synced_from ?? "-"} />
    </View>
  );
}

function DraftsScreen() {
  const [showAllDrafts, setShowAllDrafts] = useState(false);
  const drafts = useJournalDrafts(1, 20, showAllDrafts);
  const createJournalEntry = useCreateJournalEntry();
  const [form, setForm] = useState<JournalEntryFormState>(() => defaultJournalEntryForm());
  const [formMessage, setFormMessage] = useState("");

  if (drafts.isLoading) return <Loading />;
  if (drafts.isError) return <ErrorText message={drafts.error.message} />;

  const selectedDraft = (drafts.data?.drafts ?? []).find((item) => item.id === form.draftId);
  const updateForm = (key: keyof JournalEntryFormState, value: string) => {
    setForm((current) => ({ ...current, [key]: value }));
    setFormMessage("");
  };
  const selectDraft = (draftId: number) => {
    const draft = (drafts.data?.drafts ?? []).find((item) => item.id === draftId);
    if (draft && draft.draft_status !== "needs_review") {
      setForm(defaultJournalEntryForm());
      setFormMessage("작성 대기 상태의 초안만 일지로 저장할 수 있습니다.");
      return;
    }
    setForm({ ...defaultJournalEntryForm(), draftId });
    setFormMessage("");
  };
  const saveEntry = async () => {
    if (!form.draftId) {
      setFormMessage("작성할 초안을 선택하세요.");
      return;
    }
    try {
      await createJournalEntry.mutateAsync(buildJournalEntryPayload(form));
      setForm(defaultJournalEntryForm());
      setFormMessage("일지 작성을 완료했습니다.");
    } catch (error) {
      setFormMessage(error instanceof Error ? error.message : "일지 저장에 실패했습니다.");
    }
  };

  return (
    <View style={styles.panel}>
      <Text style={styles.panelTitle}>복기 대기</Text>
      <SegmentedControl
        options={[
          { key: "pending", label: "대기" },
          { key: "all", label: "전체" },
        ]}
        value={showAllDrafts ? "all" : "pending"}
        onChange={(value) => {
          setShowAllDrafts(value === "all");
          setForm(defaultJournalEntryForm());
          setFormMessage("");
        }}
      />
      <Metric label={showAllDrafts ? "전체 초안" : "복기 대기"} value={`${drafts.data?.total ?? 0}건`} />
      {selectedDraft ? (
        <View style={styles.reviewBox}>
          <Text style={styles.reviewTitle}>
            {selectedDraft.name || selectedDraft.ticker || "선택한 초안"}
          </Text>
          <Text style={styles.rowDetail}>
            {`${draftSourceLabel(selectedDraft.source_type)} · ${draftStatusLabel(selectedDraft.draft_status)}`}
          </Text>
          <FormInput label="전략" value={form.strategyName} onChangeText={(value) => updateForm("strategyName", value)} placeholder="예: ORB" />
          <FormInput label="셋업 태그" value={form.setupTags} onChangeText={(value) => updateForm("setupTags", value)} placeholder="쉼표로 구분" />
          <FormInput label="진입 근거" value={form.entryReason} onChangeText={(value) => updateForm("entryReason", value)} multiline />
          <FormInput label="청산 근거" value={form.exitReason} onChangeText={(value) => updateForm("exitReason", value)} multiline />
          <SegmentedControl
            options={[
              { key: "unknown", label: "미정" },
              { key: "followed", label: "원칙 준수" },
              { key: "broken", label: "원칙 이탈" },
            ]}
            value={form.ruleFollowed}
            onChange={(value) => updateForm("ruleFollowed", value)}
          />
          <FormInput label="잘한 점" value={form.goodPoints} onChangeText={(value) => updateForm("goodPoints", value)} multiline />
          <FormInput label="개선점" value={form.improvementPoints} onChangeText={(value) => updateForm("improvementPoints", value)} multiline />
          <FormInput label="손익 직접 입력" value={form.profitLossAmount} onChangeText={(value) => updateForm("profitLossAmount", value)} keyboardType="number-pad" />
          <FormInput label="메모" value={form.memo} onChangeText={(value) => updateForm("memo", value)} multiline />
          <Pressable
            onPress={saveEntry}
            disabled={createJournalEntry.isPending}
            style={[styles.primaryButton, createJournalEntry.isPending && styles.disabledButton]}
          >
            <Text style={styles.primaryButtonText}>
              {createJournalEntry.isPending ? "저장 중" : "일지 작성 완료"}
            </Text>
          </Pressable>
        </View>
      ) : null}
      {formMessage ? <Text style={styles.formMessage}>{formMessage}</Text> : null}
      {(drafts.data?.drafts ?? []).length === 0 ? (
        <Text style={styles.muted}>표시할 초안이 없습니다.</Text>
      ) : null}
      {(drafts.data?.drafts ?? []).map((item) => {
        const canWrite = item.draft_status === "needs_review";
        return (
          <View key={item.id} style={styles.row}>
            <View style={styles.rowBody}>
              <Text style={styles.rowTitle}>{item.name || item.ticker || "미분류"}</Text>
              <Text style={styles.rowDetail}>
                {`${draftSourceLabel(item.source_type)} · ${draftStatusLabel(item.draft_status)}`}
              </Text>
            </View>
            <Pressable
              onPress={() => selectDraft(item.id)}
              disabled={!canWrite}
              style={[styles.smallButton, !canWrite && styles.disabledButton]}
            >
              <Text style={styles.smallButtonText}>{canWrite ? "작성" : draftStatusActionLabel(item.draft_status)}</Text>
            </Pressable>
          </View>
        );
      })}
    </View>
  );
}

function JournalEntriesScreen() {
  const entries = useJournalEntries();
  const saveJournalEntry = useCreateJournalEntry();
  const deleteJournalEntry = useDeleteJournalEntry();
  const [form, setForm] = useState<JournalEntryFormState>(() => defaultJournalEntryForm());
  const [editingEntryId, setEditingEntryId] = useState<number | null>(null);
  const [formMessage, setFormMessage] = useState("");

  if (entries.isLoading) return <Loading />;
  if (entries.isError) return <ErrorText message={entries.error.message} />;

  const updateForm = (key: keyof JournalEntryFormState, value: string) => {
    setForm((current) => ({ ...current, [key]: value }));
    setFormMessage("");
  };
  const startEdit = (entry: JournalEntry) => {
    setEditingEntryId(entry.id);
    setForm(journalEntryToForm(entry));
    setFormMessage("");
  };
  const cancelEdit = () => {
    setEditingEntryId(null);
    setForm(defaultJournalEntryForm());
    setFormMessage("");
  };
  const saveEdit = async () => {
    if (!form.draftId) {
      setFormMessage("수정할 일지를 선택하세요.");
      return;
    }
    try {
      await saveJournalEntry.mutateAsync(buildJournalEntryPayload(form));
      setEditingEntryId(null);
      setForm(defaultJournalEntryForm());
      setFormMessage("일지를 수정했습니다.");
    } catch (error) {
      setFormMessage(error instanceof Error ? error.message : "일지 수정에 실패했습니다.");
    }
  };
  const removeEntry = async (entryId: number) => {
    try {
      await deleteJournalEntry.mutateAsync(entryId);
      if (editingEntryId === entryId) {
        setEditingEntryId(null);
        setForm(defaultJournalEntryForm());
      }
      setFormMessage("일지를 삭제했습니다.");
    } catch (error) {
      setFormMessage(error instanceof Error ? error.message : "일지 삭제에 실패했습니다.");
    }
  };

  return (
    <View style={styles.panel}>
      <Text style={styles.panelTitle}>작성 완료 일지</Text>
      <Metric label="전체" value={`${entries.data?.total ?? 0}건`} />
      {editingEntryId ? (
        <View style={styles.reviewBox}>
          <Text style={styles.reviewTitle}>일지 수정</Text>
          <FormInput label="전략" value={form.strategyName} onChangeText={(value) => updateForm("strategyName", value)} placeholder="예: ORB" />
          <FormInput label="셋업 태그" value={form.setupTags} onChangeText={(value) => updateForm("setupTags", value)} placeholder="쉼표로 구분" />
          <FormInput label="진입 근거" value={form.entryReason} onChangeText={(value) => updateForm("entryReason", value)} multiline />
          <FormInput label="청산 근거" value={form.exitReason} onChangeText={(value) => updateForm("exitReason", value)} multiline />
          <SegmentedControl
            options={[
              { key: "unknown", label: "미정" },
              { key: "followed", label: "원칙 준수" },
              { key: "broken", label: "원칙 이탈" },
            ]}
            value={form.ruleFollowed}
            onChange={(value) => updateForm("ruleFollowed", value)}
          />
          <FormInput label="잘한 점" value={form.goodPoints} onChangeText={(value) => updateForm("goodPoints", value)} multiline />
          <FormInput label="개선점" value={form.improvementPoints} onChangeText={(value) => updateForm("improvementPoints", value)} multiline />
          <FormInput label="손익 직접 입력" value={form.profitLossAmount} onChangeText={(value) => updateForm("profitLossAmount", value)} keyboardType="number-pad" />
          <FormInput label="메모" value={form.memo} onChangeText={(value) => updateForm("memo", value)} multiline />
          <View style={styles.actionRow}>
            <Pressable
              onPress={saveEdit}
              disabled={saveJournalEntry.isPending}
              style={[styles.primaryButton, styles.actionButton, saveJournalEntry.isPending && styles.disabledButton]}
            >
              <Text style={styles.primaryButtonText}>
                {saveJournalEntry.isPending ? "저장 중" : "수정 저장"}
              </Text>
            </Pressable>
            <Pressable onPress={cancelEdit} style={[styles.secondaryButton, styles.actionButton]}>
              <Text style={styles.secondaryButtonText}>취소</Text>
            </Pressable>
          </View>
        </View>
      ) : null}
      {formMessage ? <Text style={styles.formMessage}>{formMessage}</Text> : null}
      {(entries.data?.entries ?? []).map((entry) => (
        <View key={entry.id} style={styles.row}>
          <View style={styles.rowBody}>
            <Text style={styles.rowTitle}>{entry.name || entry.ticker || "미분류"}</Text>
            <Text style={styles.rowDetail}>
              {`${entry.strategy_name || "전략 미지정"} · ${formatKrw(entry.manual_profit_loss_amount ?? 0)}원`}
            </Text>
            <RelatedOrderExecutionsSummary entry={entry} />
          </View>
          <View style={styles.rowActions}>
            <Pressable onPress={() => startEdit(entry)} style={styles.smallButton}>
              <Text style={styles.smallButtonText}>수정</Text>
            </Pressable>
            <Pressable
              onPress={() => removeEntry(entry.id)}
              disabled={deleteJournalEntry.isPending}
              style={styles.deleteButton}
            >
              <Text style={styles.deleteButtonText}>삭제</Text>
            </Pressable>
          </View>
        </View>
      ))}
    </View>
  );
}

function ManualTransactionsScreen() {
  const transactions = useManualTransactions();
  const createManualTransaction = useCreateManualTransaction();
  const importManualTransactionsCsv = useImportManualTransactionsCsv();
  const importManualTransactionsCsvFile = useImportManualTransactionsCsvFile();
  const loadCsvTemplate = useManualTransactionsCsvTemplate();
  const deleteManualTransaction = useDeleteManualTransaction();
  const [form, setForm] = useState<ManualFormState>(() => defaultManualForm());
  const [csvText, setCsvText] = useState("");
  const [csvAsset, setCsvAsset] = useState<DocumentPicker.DocumentPickerAsset | null>(null);
  const [csvFileName, setCsvFileName] = useState("");
  const [csvImportErrors, setCsvImportErrors] = useState<ManualTransactionsImportError[]>([]);
  const [formMessage, setFormMessage] = useState("");

  if (transactions.isLoading) return <Loading />;
  if (transactions.isError) return <ErrorText message={transactions.error.message} />;

  const updateForm = (key: keyof ManualFormState, value: string) => {
    setForm((current) => ({ ...current, [key]: value }));
    setFormMessage("");
  };

  const saveTransaction = async () => {
    if (!form.tradeDate.trim()) {
      setFormMessage("거래일을 입력하세요.");
      return;
    }
    try {
      await createManualTransaction.mutateAsync(buildManualPayload(form));
      setForm(defaultManualForm());
      setFormMessage("수동 거래를 저장했습니다.");
    } catch (error) {
      setFormMessage(error instanceof Error ? error.message : "저장에 실패했습니다.");
    }
  };

  const removeTransaction = async (transactionId: number) => {
    try {
      await deleteManualTransaction.mutateAsync(transactionId);
      setFormMessage("수동 거래를 삭제했습니다.");
    } catch (error) {
      setFormMessage(error instanceof Error ? error.message : "삭제에 실패했습니다.");
    }
  };

  const importCsv = async () => {
    if (!csvText.trim() && !csvAsset) {
      setFormMessage("가져올 CSV 내용을 붙여넣거나 파일을 선택하세요.");
      return;
    }
    try {
      const result = csvAsset
        ? await importManualTransactionsCsvFile.mutateAsync(buildCsvFormData(csvAsset))
        : await importManualTransactionsCsv.mutateAsync(csvText);
      setCsvText("");
      setCsvAsset(null);
      setCsvFileName("");
      setCsvImportErrors(result.errors || []);
      setFormMessage(
        `CSV 가져오기 완료: ${result.imported_count}건 저장, ${result.failed_count}건 실패, ${result.skipped_count}건 건너뜀`,
      );
    } catch (error) {
      setCsvImportErrors([]);
      setFormMessage(error instanceof Error ? error.message : "CSV 가져오기에 실패했습니다.");
    }
  };

  const pickCsvFile = async () => {
    try {
      const result = await DocumentPicker.getDocumentAsync({
        type: ["text/csv", "text/comma-separated-values", "application/csv", "application/vnd.ms-excel", "*/*"],
        copyToCacheDirectory: true,
        multiple: false,
        base64: false,
      });
      if (result.canceled) return;

      const asset = result.assets[0];
      setCsvText("");
      setCsvAsset(asset);
      setCsvFileName(asset.name);
      setCsvImportErrors([]);
      setFormMessage(`CSV 파일을 불러왔습니다: ${asset.name}`);
    } catch (error) {
      setCsvImportErrors([]);
      setFormMessage(error instanceof Error ? error.message : "CSV 파일을 읽지 못했습니다.");
    }
  };

  const fillCsvTemplate = async () => {
    try {
      const template = await loadCsvTemplate.mutateAsync();
      setCsvText(template.replace(/^\uFEFF/, ""));
      setCsvAsset(null);
      setCsvFileName("");
      setCsvImportErrors([]);
      setFormMessage("CSV 템플릿을 불러왔습니다.");
    } catch (error) {
      setCsvImportErrors([]);
      setFormMessage(error instanceof Error ? error.message : "CSV 템플릿을 불러오지 못했습니다.");
    }
  };

  return (
    <View style={styles.panel}>
      <Text style={styles.panelTitle}>수동 입력</Text>
      <View style={styles.formGrid}>
        <FormInput label="거래일" value={form.tradeDate} onChangeText={(value) => updateForm("tradeDate", value)} placeholder="YYYY-MM-DD" />
        <FormInput label="증권사" value={form.broker} onChangeText={(value) => updateForm("broker", value)} placeholder="MANUAL" />
        <FormInput label="계좌" value={form.accountName} onChangeText={(value) => updateForm("accountName", value)} placeholder="기타" />
        <FormInput label="유형" value={form.transactionType} onChangeText={(value) => updateForm("transactionType", value)} placeholder="buy/sell/dividend" />
        <FormInput label="종목코드" value={form.ticker} onChangeText={(value) => updateForm("ticker", value)} placeholder="005930" />
        <FormInput label="종목명" value={form.name} onChangeText={(value) => updateForm("name", value)} placeholder="삼성전자" />
        <FormInput label="수량" value={form.quantity} onChangeText={(value) => updateForm("quantity", value)} keyboardType="decimal-pad" />
        <FormInput label="가격" value={form.price} onChangeText={(value) => updateForm("price", value)} keyboardType="number-pad" />
        <FormInput label="매매손익" value={form.profitLossAmount} onChangeText={(value) => updateForm("profitLossAmount", value)} keyboardType="number-pad" />
        <FormInput label="배당" value={form.dividendAmount} onChangeText={(value) => updateForm("dividendAmount", value)} keyboardType="number-pad" />
        <FormInput label="세금" value={form.taxAmount} onChangeText={(value) => updateForm("taxAmount", value)} keyboardType="number-pad" />
        <FormInput label="수수료" value={form.commissionAmount} onChangeText={(value) => updateForm("commissionAmount", value)} keyboardType="number-pad" />
        <FormInput label="통화" value={form.currency} onChangeText={(value) => updateForm("currency", value)} placeholder="KRW" />
        <FormInput label="메모" value={form.memo} onChangeText={(value) => updateForm("memo", value)} placeholder="수동 입력 메모" multiline />
      </View>
      <Pressable
        onPress={saveTransaction}
        disabled={createManualTransaction.isPending}
        style={[styles.primaryButton, createManualTransaction.isPending && styles.disabledButton]}
      >
        <Text style={styles.primaryButtonText}>
          {createManualTransaction.isPending ? "저장 중" : "수동 거래 저장"}
        </Text>
      </Pressable>
      <View style={styles.csvImportBox}>
        <Text style={styles.reviewTitle}>CSV 가져오기</Text>
        <Text style={styles.muted}>
          타 증권사 거래내역을 CSV 파일로 선택하거나 붙여넣으면 수동 입력 목록에 저장됩니다.
        </Text>
        {csvFileName ? <Text style={styles.rowDetail}>{`선택 파일: ${csvFileName}`}</Text> : null}
        <TextInput
          testID="manual-csv-input"
          value={csvText}
          onChangeText={(value) => {
            setCsvText(value);
            setCsvAsset(null);
            setCsvFileName("");
            setCsvImportErrors([]);
            setFormMessage("");
          }}
          placeholder={manualCsvSampleText}
          multiline
          style={[styles.textInput, styles.csvInput]}
          placeholderTextColor="#94a3b8"
        />
        <View style={styles.csvActionRow}>
          <Pressable
            testID="manual-csv-template-button"
            onPress={fillCsvTemplate}
            disabled={loadCsvTemplate.isPending}
            style={[
              styles.secondaryButton,
              styles.csvActionButton,
              loadCsvTemplate.isPending && styles.disabledButton,
            ]}
          >
            <Text style={styles.secondaryButtonText}>
              {loadCsvTemplate.isPending ? "로딩" : "템플릿"}
            </Text>
          </Pressable>
          <Pressable
            testID="manual-csv-pick-file-button"
            onPress={pickCsvFile}
            style={[styles.secondaryButton, styles.csvActionButton]}
          >
            <Text style={styles.secondaryButtonText}>파일</Text>
          </Pressable>
          <Pressable
            testID="manual-csv-fill-sample-button"
            onPress={() => {
              setCsvText(manualCsvSampleText);
              setCsvAsset(null);
              setCsvFileName("");
              setCsvImportErrors([]);
              setFormMessage("");
            }}
            style={[styles.secondaryButton, styles.csvActionButton]}
          >
            <Text style={styles.secondaryButtonText}>샘플</Text>
          </Pressable>
          <Pressable
            testID="manual-csv-import-button"
            onPress={importCsv}
            disabled={importManualTransactionsCsv.isPending || importManualTransactionsCsvFile.isPending}
            style={[
              styles.secondaryButton,
              styles.csvActionButton,
              (importManualTransactionsCsv.isPending || importManualTransactionsCsvFile.isPending) &&
                styles.disabledButton,
            ]}
          >
            <Text style={styles.secondaryButtonText}>
              {importManualTransactionsCsv.isPending || importManualTransactionsCsvFile.isPending
                ? "처리 중"
                : "가져오기"}
            </Text>
          </Pressable>
        </View>
      </View>
      {formMessage ? <Text style={styles.formMessage}>{formMessage}</Text> : null}
      {csvImportErrors.length ? (
        <View style={styles.csvErrorBox}>
          <Text style={styles.csvErrorTitle}>가져오기 실패 행</Text>
          {csvImportErrors.slice(0, 5).map((error, index) => (
            <Text key={`${error.row ?? index}`} style={styles.csvErrorText}>
              {`행 ${String(error.row ?? "-")}: ${String(error.message ?? "확인 필요")}`}
            </Text>
          ))}
          {csvImportErrors.length > 5 ? (
            <Text style={styles.csvErrorText}>{`외 ${csvImportErrors.length - 5}건`}</Text>
          ) : null}
        </View>
      ) : null}
      <Metric label="전체" value={`${transactions.data?.total ?? 0}건`} />
      {(transactions.data?.transactions ?? []).map((item) => (
        <View key={item.id} style={styles.row}>
          <View style={styles.rowBody}>
            <Text style={styles.rowTitle}>{item.name || item.ticker || item.broker}</Text>
            <Text style={styles.rowDetail}>
              {`${item.trade_date} · ${item.currency} · ${item.transaction_type}`}
            </Text>
          </View>
          <Pressable
            onPress={() => removeTransaction(item.id)}
            disabled={deleteManualTransaction.isPending}
            style={styles.deleteButton}
          >
            <Text style={styles.deleteButtonText}>삭제</Text>
          </Pressable>
        </View>
      ))}
    </View>
  );
}

function AnalyticsScreen() {
  const [rangeKey, setRangeKey] = useState<AnalyticsRangeKey>("1y");
  const [profitBasis, setProfitBasis] = useState<ProfitBasisKey>("monthly");
  const [allocationBasis, setAllocationBasis] = useState<AllocationBasisKey>("ticker");
  const selectedRange = getAnalyticsDateRange(rangeKey);
  const analytics = useJournalAnalytics(selectedRange);
  const { width } = useWindowDimensions();
  const chartWidth = Math.min(width - 64, 340);

  if (analytics.isLoading) return <Loading />;
  if (analytics.isError) return <ErrorText message={analytics.error.message} />;

  const profitBars = toProfitBarData(getProfitRows(analytics.data, profitBasis));
  const trendLine = toTrendLineData(analytics.data?.profit_trend ?? []);
  const allocationPie = toAllocationPieData(
    getAllocationRows(analytics.data, allocationBasis),
    allocationBasis,
  );
  const dividendBars = toAmountBarData(analytics.data?.dividend_by_year ?? [], "#047857");
  const taxBars = toAmountBarData(analytics.data?.tax_by_year ?? [], "#dc2626");
  const commissionBars = toAmountBarData(analytics.data?.commission_by_year ?? [], "#f59e0b");
  const hasCostBars = taxBars.length > 0 || commissionBars.length > 0;

  return (
    <View style={styles.panel}>
      <Text style={styles.panelTitle}>분석</Text>
      <View style={styles.filterRow}>
        {analyticsRanges.map((range) => (
          <Pressable
            key={range.key}
            testID={`analytics-range-${range.key}`}
            onPress={() => setRangeKey(range.key)}
            style={[styles.filterButton, rangeKey === range.key && styles.activeFilterButton]}
          >
            <Text
              style={[
                styles.filterText,
                rangeKey === range.key && styles.activeFilterText,
              ]}
            >
              {range.label}
            </Text>
          </Pressable>
        ))}
      </View>
      <Text style={styles.filterCaption}>{formatAnalyticsRangeLabel(selectedRange)}</Text>
      <Metric label="거래 수" value={`${analytics.data?.total_entries ?? 0}건`} />
      <Metric label="총손익" value={`${formatKrw(analytics.data?.realized_profit_loss_total)}원`} />
      <Metric label="승률" value={analytics.data?.win_rate == null ? "-" : `${analytics.data.win_rate}%`} />
      {(analytics.data?.total_entries ?? 0) === 0 ? (
        <AnalyticsNotice testID="analytics-empty-range" message="선택 기간에 집계된 거래가 없습니다." />
      ) : null}
      <ChartBlock title={`${profitBasisLabel(profitBasis)} 수익`} testID="analytics-profit-chart">
        <SegmentedControl
          options={profitBasisOptions}
          value={profitBasis}
          onChange={setProfitBasis}
          testIDPrefix="analytics-profit-basis"
        />
        {profitBars.length ? (
          <BarChart
            data={profitBars}
            width={chartWidth}
            height={170}
            barWidth={profitBars.length > 8 ? 16 : 24}
            spacing={profitBars.length > 8 ? 12 : 18}
            noOfSections={4}
            hideRules
            yAxisThickness={0}
            xAxisThickness={0}
            yAxisTextStyle={styles.chartAxis}
            xAxisLabelTextStyle={styles.chartAxis}
            isAnimated
          />
        ) : (
          <EmptyChart testID="analytics-profit-empty" message={`${profitBasisLabel(profitBasis)} 수익 데이터가 없습니다.`} />
        )}
      </ChartBlock>
      <ChartBlock title="수익 추이" testID="analytics-trend-chart">
        {trendLine.length ? (
          <LineChart
            data={trendLine}
            width={chartWidth}
            height={170}
            thickness={3}
            color="#2563eb"
            dataPointsColor="#2563eb"
            noOfSections={4}
            hideRules
            yAxisThickness={0}
            xAxisThickness={0}
            yAxisTextStyle={styles.chartAxis}
            xAxisLabelTextStyle={styles.chartAxis}
            curved
            isAnimated
          />
        ) : (
          <EmptyChart testID="analytics-trend-empty" message="수익 추이 데이터가 없습니다." />
        )}
      </ChartBlock>
      <ChartBlock
        title={`${allocationBasisLabel(allocationBasis)} 비중`}
        testID="analytics-allocation-chart"
      >
        <SegmentedControl
          options={allocationBasisOptions}
          value={allocationBasis}
          onChange={setAllocationBasis}
          testIDPrefix="analytics-allocation-basis"
        />
        {allocationPie.length ? (
          <View style={styles.pieRow}>
            <PieChart
              data={allocationPie}
              donut
              radius={82}
              innerRadius={48}
              showText
              textColor="#07111f"
              textSize={10}
            />
            <View style={styles.legend}>
              {allocationPie.map((item) => (
                <View key={item.text} style={styles.legendItem}>
                  <View style={[styles.legendSwatch, { backgroundColor: item.color }]} />
                  <Text style={styles.legendText}>{item.text}</Text>
                </View>
              ))}
            </View>
          </View>
        ) : (
          <EmptyChart testID="analytics-allocation-empty" message={`${allocationBasisLabel(allocationBasis)} 비중 데이터가 없습니다.`} />
        )}
      </ChartBlock>
      <ChartBlock title="배당" testID="analytics-dividend-chart">
        <Metric label="배당 합계" value={`${formatKrw(analytics.data?.dividend_total)}원`} />
        {dividendBars.length ? (
          <BarChart
            data={dividendBars}
            width={chartWidth}
            height={150}
            barWidth={28}
            spacing={20}
            noOfSections={4}
            hideRules
            yAxisThickness={0}
            xAxisThickness={0}
            yAxisTextStyle={styles.chartAxis}
            xAxisLabelTextStyle={styles.chartAxis}
            isAnimated
          />
        ) : (
          <EmptyChart testID="analytics-dividend-empty" message="배당 데이터가 없습니다." />
        )}
      </ChartBlock>
      <ChartBlock title="세금/수수료" testID="analytics-cost-chart">
        <View style={styles.metricGrid}>
          <Metric label="세금 합계" value={`${formatKrw(analytics.data?.tax_total)}원`} />
          <Metric label="수수료 합계" value={`${formatKrw(analytics.data?.commission_total)}원`} />
        </View>
        {hasCostBars ? (
          <>
            {taxBars.length ? (
              <>
                <Text style={styles.chartCaption}>세금</Text>
                <BarChart
                  data={taxBars}
                  width={chartWidth}
                  height={150}
                  barWidth={28}
                  spacing={20}
                  noOfSections={4}
                  hideRules
                  yAxisThickness={0}
                  xAxisThickness={0}
                  yAxisTextStyle={styles.chartAxis}
                  xAxisLabelTextStyle={styles.chartAxis}
                  isAnimated
                />
              </>
            ) : null}
            {commissionBars.length ? (
              <>
                <Text style={styles.chartCaption}>수수료</Text>
                <BarChart
                  data={commissionBars}
                  width={chartWidth}
                  height={120}
                  barWidth={28}
                  spacing={20}
                  noOfSections={3}
                  hideRules
                  yAxisThickness={0}
                  xAxisThickness={0}
                  yAxisTextStyle={styles.chartAxis}
                  xAxisLabelTextStyle={styles.chartAxis}
                  isAnimated
                />
              </>
            ) : null}
          </>
        ) : (
          <EmptyChart testID="analytics-cost-empty" message="세금/수수료 데이터가 없습니다." />
        )}
      </ChartBlock>
    </View>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <View style={styles.metric}>
      <Text style={styles.metricLabel}>{label}</Text>
      <Text style={styles.metricValue}>{value}</Text>
    </View>
  );
}

function ListRow({ title, detail }: { title: string; detail: string }) {
  return (
    <View style={styles.row}>
      <Text style={styles.rowTitle}>{title}</Text>
      <Text style={styles.rowDetail}>{detail}</Text>
    </View>
  );
}

function FormInput({
  label,
  value,
  onChangeText,
  placeholder,
  keyboardType,
  multiline = false,
}: {
  label: string;
  value: string;
  onChangeText: (value: string) => void;
  placeholder?: string;
  keyboardType?: KeyboardTypeOptions;
  multiline?: boolean;
}) {
  return (
    <View style={styles.formField}>
      <Text style={styles.formLabel}>{label}</Text>
      <TextInput
        value={value}
        onChangeText={onChangeText}
        placeholder={placeholder}
        keyboardType={keyboardType}
        multiline={multiline}
        style={[styles.textInput, multiline && styles.multilineInput]}
        placeholderTextColor="#94a3b8"
      />
    </View>
  );
}

function SegmentedControl<TKey extends string>({
  options,
  value,
  onChange,
  testIDPrefix,
}: {
  options: Array<{ key: TKey; label: string }>;
  value: TKey;
  onChange: (value: TKey) => void;
  testIDPrefix?: string;
}) {
  return (
    <View style={styles.segmentRow}>
      {options.map((option) => (
        <Pressable
          key={option.key}
          testID={testIDPrefix ? `${testIDPrefix}-${option.key}` : undefined}
          onPress={() => onChange(option.key)}
          style={[styles.segmentButton, value === option.key && styles.activeSegmentButton]}
        >
          <Text
            style={[
              styles.segmentText,
              value === option.key && styles.activeSegmentText,
            ]}
          >
            {option.label}
          </Text>
        </Pressable>
      ))}
    </View>
  );
}

function ChartBlock({
  title,
  children,
  testID,
}: {
  title: string;
  children: React.ReactNode;
  testID?: string;
}) {
  return (
    <View testID={testID} style={styles.chartBlock}>
      <Text style={styles.chartTitle}>{title}</Text>
      {children}
    </View>
  );
}

function AnalyticsNotice({ message, testID }: { message: string; testID?: string }) {
  return (
    <View testID={testID} style={styles.analyticsNotice}>
      <Text style={styles.analyticsNoticeText}>{message}</Text>
    </View>
  );
}

function RelatedOrderExecutionsSummary({ entry }: { entry: JournalEntry }) {
  const executions = relatedOrderExecutions(entry);
  if (!executions.length) return null;

  return (
    <View style={styles.linkedExecutionBox}>
      <Text style={styles.linkedExecutionTitle}>연결된 체결 상세 {executions.length}건</Text>
      {executions.slice(0, 3).map((execution, index) => (
        <Text key={`${execution.source_key || execution.order_no || index}`} style={styles.linkedExecutionText}>
          {formatOrderExecutionLine(execution)}
        </Text>
      ))}
      {executions.length > 3 ? (
        <Text style={styles.linkedExecutionText}>외 {executions.length - 3}건 더 있음</Text>
      ) : null}
    </View>
  );
}

function EmptyChart({
  message = "표시할 차트 데이터가 없습니다.",
  testID,
}: {
  message?: string;
  testID?: string;
}) {
  return <Text testID={testID} style={styles.muted}>{message}</Text>;
}

function Loading() {
  return (
    <View style={styles.center}>
      <ActivityIndicator size="large" />
      <Text style={styles.muted}>불러오는 중</Text>
    </View>
  );
}

function ErrorText({ message }: { message: string }) {
  return (
    <View style={styles.panel}>
      <Text style={styles.error}>데이터를 불러오는 중 오류가 발생했습니다.</Text>
      <Text style={styles.muted}>{message}</Text>
    </View>
  );
}

function formatKrw(value?: number) {
  return Number(value || 0).toLocaleString("ko-KR");
}

function relatedOrderExecutions(entry: JournalEntry): RelatedOrderExecution[] {
  return entry.source_payload?.related_order_executions ?? [];
}

function formatOrderExecutionLine(execution: RelatedOrderExecution) {
  const side = execution.trade_side_name || "체결";
  const status = execution.order_status || "상태 미확인";
  const time = formatOrderExecutionTime(execution.confirm_time || execution.order_time);
  const price = execution.filled_price ?? execution.order_price;
  const quantity = execution.filled_quantity ?? execution.order_quantity;
  const priceText = price == null ? "단가 -" : `${formatKrw(price)}원`;
  const quantityText = quantity == null ? "수량 -" : `${formatKrw(quantity)}주`;
  return `${time} · ${side}/${status} · ${priceText} · ${quantityText}`;
}

function formatOrderExecutionTime(value?: string | null) {
  const digits = String(value || "").replace(/\D/g, "");
  if (digits.length >= 6) return `${digits.slice(0, 2)}:${digits.slice(2, 4)}:${digits.slice(4, 6)}`;
  if (digits.length >= 4) return `${digits.slice(0, 2)}:${digits.slice(2, 4)}`;
  return "시간 -";
}

function draftSourceLabel(value: string) {
  if (value === "trade_journal") return "매매 요약";
  if (value === "order_execution") return "체결 상세";
  return value || "원천 미확인";
}

function draftStatusLabel(value: string) {
  if (value === "needs_review") return "복기 대기";
  if (value === "completed") return "작성 완료";
  if (value === "linked") return "완료 일지에 연결";
  return value || "상태 미확인";
}

function draftStatusActionLabel(value: string) {
  if (value === "completed") return "완료";
  if (value === "linked") return "연결됨";
  return "확인";
}

function buildCsvFormData(asset: DocumentPicker.DocumentPickerAsset) {
  const formData = new FormData();
  if (asset.file) {
    formData.append("file", asset.file, asset.name);
    return formData;
  }

  formData.append("file", {
    uri: asset.uri,
    name: asset.name || "manual-transactions.csv",
    type: asset.mimeType || "text/csv",
  } as unknown as Blob);
  return formData;
}

function buildManualPayload(form: ManualFormState) {
  return {
    trade_date: form.tradeDate.trim(),
    broker: form.broker.trim() || "MANUAL",
    account_name: form.accountName.trim() || "기타",
    transaction_type: form.transactionType.trim() || "trade",
    ticker: form.ticker.trim().toUpperCase(),
    name: form.name.trim(),
    quantity: numberOrNull(form.quantity),
    price: integerOrNull(form.price),
    profit_loss_amount: integerOrNull(form.profitLossAmount),
    dividend_amount: integerOrNull(form.dividendAmount),
    tax_amount: integerOrNull(form.taxAmount),
    commission_amount: integerOrNull(form.commissionAmount),
    currency: form.currency.trim().toUpperCase() || "KRW",
    memo: form.memo.trim(),
  };
}

function buildJournalEntryPayload(form: JournalEntryFormState) {
  return {
    draft_id: Number(form.draftId),
    strategy_name: form.strategyName.trim(),
    setup_tags: splitTags(form.setupTags),
    entry_reason: form.entryReason.trim(),
    exit_reason: form.exitReason.trim(),
    rule_followed: ruleFollowedValue(form.ruleFollowed),
    good_points: form.goodPoints.trim(),
    improvement_points: form.improvementPoints.trim(),
    memo: form.memo.trim(),
    manual_profit_loss_amount: integerOrNull(form.profitLossAmount),
  };
}

function splitTags(value: string) {
  return value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

function ruleFollowedValue(value: JournalEntryFormState["ruleFollowed"]) {
  if (value === "followed") return true;
  if (value === "broken") return false;
  return null;
}

function journalEntryToForm(entry: JournalEntry): JournalEntryFormState {
  return {
    draftId: entry.draft_id,
    strategyName: entry.strategy_name || "",
    setupTags: (entry.setup_tags || []).join(", "),
    entryReason: entry.entry_reason || "",
    exitReason: entry.exit_reason || "",
    ruleFollowed: ruleFollowedKey(entry.rule_followed),
    goodPoints: entry.good_points || "",
    improvementPoints: entry.improvement_points || "",
    memo: entry.memo || "",
    profitLossAmount:
      entry.manual_profit_loss_amount == null
        ? ""
        : String(entry.manual_profit_loss_amount),
  };
}

function ruleFollowedKey(value: boolean | null | undefined): JournalEntryFormState["ruleFollowed"] {
  if (value === true) return "followed";
  if (value === false) return "broken";
  return "unknown";
}

function numberOrNull(value: string) {
  const normalized = value.replaceAll(",", "").trim();
  if (!normalized) return null;
  const parsed = Number(normalized);
  return Number.isFinite(parsed) ? parsed : null;
}

function integerOrNull(value: string) {
  const parsed = numberOrNull(value);
  return parsed == null ? null : Math.round(parsed);
}

function getProfitRows(
  data: ReturnType<typeof useJournalAnalytics>["data"],
  basis: ProfitBasisKey,
) {
  if (!data) return [];
  if (basis === "annual") return data.annual_profit ?? [];
  if (basis === "quarterly") return data.quarterly_profit ?? [];
  return data.monthly_profit ?? [];
}

function getAllocationRows(
  data: ReturnType<typeof useJournalAnalytics>["data"],
  basis: AllocationBasisKey,
) {
  if (!data) return [];
  if (basis === "type") return data.type_allocation ?? [];
  if (basis === "account") return data.account_allocation ?? [];
  return data.ticker_allocation ?? [];
}

function toProfitBarData(rows: Array<Record<string, unknown>>) {
  const bars = rows
    .slice(0, 10)
    .reverse()
    .map((row) => {
      const value = toFiniteNumber(row.profit_loss_total);
      const period = String(row.period || "").replace(String(new Date().getFullYear()), "");
      return {
        value,
        label: period || "-",
        frontColor: value < 0 ? "#dc2626" : "#047857",
      };
    });
  return hasNonZeroValue(bars) ? bars : [];
}

function toAmountBarData(rows: Array<Record<string, unknown>>, color: string) {
  return rows
    .slice(0, 6)
    .reverse()
    .map((row) => ({
      value: Math.max(toFiniteNumber(row.amount), 0),
      label: String(row.period || "").replace(String(new Date().getFullYear()), "") || "-",
      frontColor: color,
    }))
    .filter((row) => row.value > 0);
}

function toTrendLineData(rows: Array<Record<string, unknown>>) {
  const points = rows.slice(-12).map((row) => ({
    value: toFiniteNumber(row.cumulative_profit_loss),
    label: shortDate(String(row.date || "")),
  }));
  return hasNonZeroValue(points) ? points : [];
}

function toAllocationPieData(rows: Array<Record<string, unknown>>, basis: AllocationBasisKey) {
  const colors = ["#2563eb", "#047857", "#f59e0b", "#dc2626", "#7c3aed", "#0891b2"];
  return rows
    .slice(0, 6)
    .map((row, index) => ({
      value: Math.max(toFiniteNumber(row.amount), 0),
      color: colors[index % colors.length],
      text: allocationRowLabel(row, basis),
    }))
    .filter((row) => row.value > 0);
}

function toFiniteNumber(value: unknown) {
  const numberValue = Number(value ?? 0);
  return Number.isFinite(numberValue) ? numberValue : 0;
}

function hasNonZeroValue(rows: Array<{ value: number }>) {
  return rows.some((row) => Math.abs(row.value) > 0);
}

function allocationRowLabel(row: Record<string, unknown>, basis: AllocationBasisKey) {
  if (basis === "type") return String(row.transaction_type || "기타");
  if (basis === "account") return String(row.account_name || "기타");
  return String(row.ticker || "기타");
}

function profitBasisLabel(key: ProfitBasisKey) {
  return profitBasisOptions.find((option) => option.key === key)?.label ?? "월간";
}

function allocationBasisLabel(key: AllocationBasisKey) {
  return allocationBasisOptions.find((option) => option.key === key)?.label ?? "종목별";
}

function shortDate(value: string) {
  if (!value || value === "UNKNOWN") return "-";
  const parts = value.split("-");
  return parts.length >= 3 ? `${parts[1]}/${parts[2]}` : value;
}

function getAnalyticsDateRange(key: AnalyticsRangeKey) {
  if (key === "all") return {};

  const end = new Date();
  end.setHours(0, 0, 0, 0);
  const start = new Date(end);
  if (key === "1m") start.setMonth(start.getMonth() - 1);
  if (key === "3m") start.setMonth(start.getMonth() - 3);
  if (key === "6m") start.setMonth(start.getMonth() - 6);
  if (key === "1y") start.setFullYear(start.getFullYear() - 1);

  return {
    startDate: formatDateParam(start),
    endDate: formatDateParam(end),
  };
}

function formatDateParam(value: Date) {
  const year = value.getFullYear();
  const month = String(value.getMonth() + 1).padStart(2, "0");
  const day = String(value.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function formatAnalyticsRangeLabel(range: { startDate?: string; endDate?: string }) {
  if (!range.startDate || !range.endDate) return "전체 기간";
  return `${range.startDate} ~ ${range.endDate}`;
}

const styles = StyleSheet.create({
  safeArea: {
    flex: 1,
    backgroundColor: "#f4f7fb",
  },
  header: {
    paddingHorizontal: 20,
    paddingTop: 16,
    paddingBottom: 10,
  },
  title: {
    color: "#07111f",
    fontSize: 28,
    fontWeight: "800",
  },
  subtitle: {
    color: "#607085",
    marginTop: 4,
  },
  tabs: {
    flexDirection: "row",
    gap: 8,
    paddingHorizontal: 16,
    paddingVertical: 10,
  },
  tab: {
    flex: 1,
    borderRadius: 8,
    backgroundColor: "#dfe6ef",
    paddingVertical: 12,
    alignItems: "center",
  },
  activeTab: {
    backgroundColor: "#ffffff",
    borderColor: "#cdd8e6",
    borderWidth: 1,
  },
  tabText: {
    color: "#5d6b7d",
    fontWeight: "700",
  },
  activeTabText: {
    color: "#07111f",
  },
  content: {
    padding: 16,
    paddingBottom: 40,
  },
  panel: {
    backgroundColor: "#ffffff",
    borderColor: "#d9e2ee",
    borderRadius: 8,
    borderWidth: 1,
    padding: 16,
    gap: 10,
  },
  panelTitle: {
    color: "#07111f",
    fontSize: 18,
    fontWeight: "800",
  },
  filterRow: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 8,
  },
  filterButton: {
    alignItems: "center",
    backgroundColor: "#eef3f9",
    borderColor: "#d8e2ee",
    borderRadius: 8,
    borderWidth: 1,
    minWidth: 58,
    paddingHorizontal: 10,
    paddingVertical: 8,
  },
  activeFilterButton: {
    backgroundColor: "#07111f",
    borderColor: "#07111f",
  },
  filterText: {
    color: "#536174",
    fontSize: 12,
    fontWeight: "800",
  },
  activeFilterText: {
    color: "#ffffff",
  },
  filterCaption: {
    color: "#607085",
    fontSize: 12,
    fontWeight: "700",
  },
  segmentRow: {
    flexDirection: "row",
    gap: 8,
  },
  segmentButton: {
    alignItems: "center",
    backgroundColor: "#f7f9fc",
    borderColor: "#dce5f1",
    borderRadius: 8,
    borderWidth: 1,
    flex: 1,
    paddingVertical: 8,
  },
  activeSegmentButton: {
    backgroundColor: "#e8f0ff",
    borderColor: "#2563eb",
  },
  segmentText: {
    color: "#607085",
    fontSize: 12,
    fontWeight: "800",
  },
  activeSegmentText: {
    color: "#1d4ed8",
  },
  metricGrid: {
    gap: 8,
  },
  formGrid: {
    gap: 10,
  },
  formField: {
    gap: 5,
  },
  formLabel: {
    color: "#536174",
    fontSize: 12,
    fontWeight: "800",
  },
  textInput: {
    backgroundColor: "#f8fafc",
    borderColor: "#dce5f1",
    borderRadius: 8,
    borderWidth: 1,
    color: "#07111f",
    fontSize: 15,
    minHeight: 42,
    paddingHorizontal: 12,
    paddingVertical: 9,
  },
  multilineInput: {
    minHeight: 72,
    textAlignVertical: "top",
  },
  csvImportBox: {
    backgroundColor: "#f8fafc",
    borderColor: "#dce5f1",
    borderRadius: 8,
    borderWidth: 1,
    gap: 10,
    padding: 12,
  },
  csvInput: {
    fontSize: 13,
    minHeight: 140,
    textAlignVertical: "top",
  },
  csvErrorBox: {
    backgroundColor: "#fff7ed",
    borderColor: "#fed7aa",
    borderRadius: 8,
    borderWidth: 1,
    gap: 4,
    padding: 10,
  },
  csvErrorTitle: {
    color: "#9a3412",
    fontSize: 12,
    fontWeight: "900",
  },
  csvErrorText: {
    color: "#9a3412",
    fontSize: 12,
    lineHeight: 18,
  },
  primaryButton: {
    alignItems: "center",
    backgroundColor: "#07111f",
    borderRadius: 8,
    paddingVertical: 12,
  },
  secondaryButton: {
    alignItems: "center",
    backgroundColor: "#ffffff",
    borderColor: "#cbd5e1",
    borderRadius: 8,
    borderWidth: 1,
    paddingVertical: 12,
  },
  secondaryButtonText: {
    color: "#334155",
    fontWeight: "900",
  },
  actionRow: {
    flexDirection: "row",
    gap: 8,
  },
  actionButton: {
    flex: 1,
  },
  csvActionRow: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 8,
  },
  csvActionButton: {
    flexGrow: 1,
    minWidth: 96,
  },
  disabledButton: {
    opacity: 0.55,
  },
  primaryButtonText: {
    color: "#ffffff",
    fontWeight: "900",
  },
  formMessage: {
    color: "#2563eb",
    fontSize: 12,
    fontWeight: "800",
  },
  reviewBox: {
    backgroundColor: "#f8fafc",
    borderColor: "#dce5f1",
    borderRadius: 8,
    borderWidth: 1,
    gap: 10,
    padding: 12,
  },
  reviewTitle: {
    color: "#07111f",
    fontSize: 16,
    fontWeight: "900",
  },
  linkedExecutionBox: {
    backgroundColor: "#f8fafc",
    borderColor: "#dce5f1",
    borderRadius: 8,
    borderWidth: 1,
    gap: 4,
    marginTop: 8,
    padding: 10,
  },
  linkedExecutionTitle: {
    color: "#334155",
    fontSize: 12,
    fontWeight: "900",
  },
  linkedExecutionText: {
    color: "#536174",
    fontSize: 12,
    lineHeight: 18,
  },
  metric: {
    backgroundColor: "#f7f9fc",
    borderColor: "#dce5f1",
    borderRadius: 8,
    borderWidth: 1,
    padding: 12,
  },
  metricLabel: {
    color: "#607085",
    fontSize: 12,
    fontWeight: "700",
  },
  metricValue: {
    color: "#07111f",
    fontSize: 18,
    fontWeight: "800",
    marginTop: 6,
  },
  row: {
    alignItems: "center",
    borderTopColor: "#e3ebf5",
    borderTopWidth: 1,
    flexDirection: "row",
    gap: 10,
    justifyContent: "space-between",
    paddingTop: 10,
  },
  rowBody: {
    flex: 1,
  },
  rowActions: {
    alignItems: "center",
    flexDirection: "row",
    gap: 6,
  },
  rowTitle: {
    color: "#07111f",
    fontWeight: "800",
  },
  rowDetail: {
    color: "#607085",
    marginTop: 4,
  },
  deleteButton: {
    borderColor: "#fecaca",
    borderRadius: 8,
    borderWidth: 1,
    paddingHorizontal: 10,
    paddingVertical: 7,
  },
  deleteButtonText: {
    color: "#dc2626",
    fontSize: 12,
    fontWeight: "900",
  },
  smallButton: {
    backgroundColor: "#07111f",
    borderRadius: 8,
    paddingHorizontal: 10,
    paddingVertical: 7,
  },
  smallButtonText: {
    color: "#ffffff",
    fontSize: 12,
    fontWeight: "900",
  },
  center: {
    alignItems: "center",
    gap: 10,
    padding: 30,
  },
  error: {
    color: "#c62828",
    fontWeight: "800",
  },
  muted: {
    color: "#607085",
  },
  analyticsNotice: {
    backgroundColor: "#f8fafc",
    borderColor: "#dce5f1",
    borderRadius: 8,
    borderWidth: 1,
    padding: 12,
  },
  analyticsNoticeText: {
    color: "#536174",
    fontSize: 12,
    fontWeight: "800",
  },
  chartBlock: {
    borderTopColor: "#e3ebf5",
    borderTopWidth: 1,
    gap: 10,
    marginTop: 4,
    paddingTop: 14,
  },
  chartTitle: {
    color: "#07111f",
    fontSize: 15,
    fontWeight: "800",
  },
  chartAxis: {
    color: "#607085",
    fontSize: 10,
  },
  chartCaption: {
    color: "#536174",
    fontSize: 12,
    fontWeight: "800",
  },
  pieRow: {
    alignItems: "center",
    flexDirection: "row",
    gap: 14,
  },
  legend: {
    flex: 1,
    gap: 8,
  },
  legendItem: {
    alignItems: "center",
    flexDirection: "row",
    gap: 8,
  },
  legendSwatch: {
    borderRadius: 4,
    height: 10,
    width: 10,
  },
  legendText: {
    color: "#425166",
    flexShrink: 1,
    fontSize: 12,
    fontWeight: "700",
  },
});
