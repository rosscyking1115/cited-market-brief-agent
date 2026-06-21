import type { AutomationPolicyItem, FundAttributionPlanPayload } from "@/lib/api";
import FundHoldingsParser from "@/app/components/FundHoldingsParser";

const DEMO_PLAN: FundAttributionPlanPayload = {
  title: "ETF / Fund vs Benchmark Attribution",
  target_use_case: "每天收盤後回答：基金和大盤表現差在哪裡，哪些持股造成差異。",
  first_region: "Taiwan",
  daily_trigger: "台股收盤後，等 TWSE/JPM 資料更新再跑。",
  required_inputs: [
    "ETF 持股、權重與持股日期",
    "ETF 當日報酬率或淨值/收盤價",
    "台灣加權指數當日報酬率",
    "每個持股的當日報酬率",
  ],
  first_supported_workflow: [
    "先讓使用者上傳 JPM 官網下載的持股檔",
    "系統抓 TWSE 收盤價並計算每檔持股報酬",
    "用權重 x 報酬計算貢獻",
    "輸出贏/輸大盤原因、最大貢獻、最大拖累、無法解釋殘差",
  ],
  automation_policy: [
    {
      label: "JPM ETF holdings file",
      status: "manual_first",
      note: "先支援上傳；自動下載前需確認條款。",
    },
    {
      label: "TWSE after-close prices",
      status: "allowed",
      note: "每日收盤後使用官方公開資料。",
    },
  ],
  disclaimer: "本頁提供績效歸因與教育資訊，不構成個人化投資建議或買賣建議。",
};

function policyText(status: AutomationPolicyItem["status"]) {
  if (status === "allowed") return "可自動";
  if (status === "manual_first") return "先手動";
  if (status === "needs_review") return "需確認";
  return "不做";
}

function policyClass(status: AutomationPolicyItem["status"]) {
  if (status === "allowed") return "border-up/50 bg-up/10 text-up";
  if (status === "manual_first") return "border-action/50 bg-action/10 text-action";
  if (status === "needs_review") return "border-flag/50 bg-flag/10 text-flag";
  return "border-down/50 bg-down/10 text-down";
}

export default function FundAttributionPanel({
  plan,
}: {
  plan: FundAttributionPlanPayload | null;
}) {
  const data = plan ?? DEMO_PLAN;

  return (
    <section className="overflow-hidden rounded-(--radius-card) border border-hairline bg-card">
      <div className="border-b border-hairline px-4 py-4 sm:px-5">
        <p className="th-label">下一個核心功能 · ETF 歸因分析</p>
        <div className="mt-2 grid gap-3 lg:grid-cols-[minmax(0,1fr)_320px] lg:items-start">
          <div>
            <h2 className="font-serif text-xl font-semibold leading-tight text-neutral-30 sm:text-2xl">
              每天收盤後：基金為什麼贏/輸台灣加權指數？
            </h2>
            <p className="reader-body mt-2 max-w-3xl text-neutral-70">
              {data.target_use_case}
            </p>
          </div>
          <div className="rounded-(--radius-ctl) border border-elevated bg-page/60 px-3 py-2">
            <p className="th-label">第一版市場</p>
            <p className="reader-body mt-1 font-semibold text-neutral-40">{data.first_region}</p>
            <p className="reader-meta mt-1 text-neutral-90">{data.daily_trigger}</p>
          </div>
        </div>
      </div>

      <div className="grid gap-0 lg:grid-cols-2">
        <div className="border-b border-hairline px-4 py-4 sm:px-5 lg:border-b-0 lg:border-r">
          <p className="th-label">需要的資料</p>
          <ol className="mt-3 grid gap-2">
            {data.required_inputs.map((item, index) => (
              <li key={item} className="grid grid-cols-[24px_1fr] gap-2">
                <span className="font-mono text-[12px] text-neutral-90">{index + 1}</span>
                <span className="reader-body text-neutral-50">{item}</span>
              </li>
            ))}
          </ol>
        </div>

        <div className="px-4 py-4 sm:px-5">
          <p className="th-label">第一版流程</p>
          <ol className="mt-3 grid gap-2">
            {data.first_supported_workflow.map((item, index) => (
              <li key={item} className="grid grid-cols-[24px_1fr] gap-2">
                <span className="font-mono text-[12px] text-neutral-90">{index + 1}</span>
                <span className="reader-body text-neutral-50">{item}</span>
              </li>
            ))}
          </ol>
        </div>
      </div>

      <div className="border-t border-hairline px-4 py-4 sm:px-5">
        <p className="th-label">自動化政策</p>
        <div className="mt-3 grid gap-2 md:grid-cols-2">
          {data.automation_policy.map((item) => (
            <article key={item.label} className="rounded-(--radius-ctl) border border-hairline bg-page/50 px-3 py-3">
              <div className="flex flex-wrap items-start justify-between gap-2">
                <h3 className="reader-body font-semibold text-neutral-40">{item.label}</h3>
                <span className={`rounded-(--radius-ctl) border px-1.5 py-0.5 font-mono text-[10px] ${policyClass(item.status)}`}>
                  {policyText(item.status)}
                </span>
              </div>
              <p className="reader-meta mt-2 text-neutral-90">{item.note}</p>
            </article>
          ))}
        </div>
        <p className="reader-meta mt-3 text-neutral-90">{data.disclaimer}</p>
      </div>

      <FundHoldingsParser />
    </section>
  );
}
