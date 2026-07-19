import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page } from "@playwright/test";

async function useReturningReader(page: Page, savedRegion = "TW") {
  await page.addInitScript(({ region }) => {
    localStorage.setItem("cmb-onboarding-v1", "done");
    localStorage.setItem("cmb-region-v1", region);
  }, { region: savedRegion });
}

async function expectNoSeriousAxeFindings(page: Page) {
  const results = await new AxeBuilder({ page }).analyze();
  const serious = results.violations
    .filter((item) => item.impact === "critical" || item.impact === "serious")
    .map((item) => ({
      id: item.id,
      nodes: item.nodes.length,
      samples: item.nodes.slice(0, 5).map((node) => ({
        target: node.target,
        data: node.any[0]?.data,
      })),
    }));
  expect(serious).toEqual([]);
}

async function useTheme(page: Page, theme: "light" | "dark") {
  await page.evaluate((value) => {
    localStorage.setItem("cmb-theme", value);
    document.documentElement.dataset.theme = value;
  }, theme);
  await expect(page.locator("html")).toHaveAttribute("data-theme", theme);
  // Let intentional colour transitions settle before measuring final-state contrast.
  await page.waitForTimeout(200);
}

async function expectAccessibleViewport(page: Page, width: number, height: number) {
  await page.setViewportSize({ width, height });
  for (const theme of ["light", "dark"] as const) {
    await useTheme(page, theme);
    await expectNoSeriousAxeFindings(page);
    const hasOverflow = await page.evaluate(
      () => document.documentElement.scrollWidth > document.documentElement.clientWidth,
    );
    expect(hasOverflow).toBe(false);
  }
}

test("separates the radar and brief workspaces", async ({ page }) => {
  await useReturningReader(page, "UK");
  await page.goto("/?region=uk");
  await expect(page.locator("html")).toHaveAttribute("lang", "en");
  await expect(page.getByRole("heading", { name: "Evidence-backed company brief" })).toHaveCount(0);
  await expect(page.getByRole("link", { name: "Company research" })).toBeVisible();

  await page.goto("/brief?region=kr");
  await expect(page.locator("html")).toHaveAttribute("lang", "en");
  await expect(page.getByRole("heading", { name: "Evidence-backed company brief" })).toBeVisible();
  await expect(page.locator("select")).toHaveCount(0);
  await expect(page.getByRole("button", { name: /Original/ })).toHaveAttribute("aria-pressed", "true");
  expect(await page.evaluate(() => localStorage.getItem("cmb-region-v1"))).toBe("UK");

  await page.goto("/");
  await expect(page.locator("select")).toHaveValue("UK");
  await expect(page.locator("html")).toHaveAttribute("lang", "en");
});

test("valid URL region overrides saved preference", async ({ page }) => {
  await useReturningReader(page, "UK");
  await page.goto("/?region=kr");
  await expect(page.locator("html")).toHaveAttribute("lang", "ko");
  await expect(page.locator("select")).toHaveValue("KR");
  await expect(page.getByText("모닝 마켓 레이더", { exact: true })).toBeVisible();
});

test("edition chooser uses a focus-trapped native dialog", async ({ page }) => {
  await page.addInitScript(() => localStorage.clear());
  await page.goto("/");
  const dialog = page.getByRole("dialog", { name: "Which region are you reading from?" });
  await expect(dialog).toBeVisible();
  await expect(dialog.locator("button").first()).toBeFocused();
  await page.keyboard.press("Shift+Tab");
  expect(await dialog.evaluate((node) => node === document.activeElement || node.contains(document.activeElement))).toBe(true);
  await dialog.getByRole("button", { name: /United Kingdom/ }).click();
  await expect(dialog).not.toBeVisible();
  await expect(page).toHaveURL(/region=uk/);
});

for (const region of ["tw", "kr", "uk", "eu"] as const) {
  test(`${region.toUpperCase()} desktop and mobile have no serious accessibility or overflow defects`, async ({ page }) => {
    await useReturningReader(page);
    await page.emulateMedia({ reducedMotion: "reduce" });
    await page.goto(`/?region=${region}`);
    await expect(page.locator("select")).toHaveValue(region.toUpperCase());
    const demoLabels = { tw: "示範資料", kr: "데모 데이터", uk: "Demo data", eu: "Demo data" };
    await expect(page.getByTestId("data-provenance")).toHaveText(demoLabels[region]);

    const expectedLang = region === "tw" ? "zh-Hant" : region === "kr" ? "ko" : "en";
    await expect(page.locator("html")).toHaveAttribute("lang", expectedLang);
    if (region === "tw" || region === "kr") {
      const structuralCopy =
        region === "tw"
          ? { skip: "跳至主要內容", nav: "工作區", theme: "深色", textSize: "文字大小" }
          : { skip: "본문으로 건너뛰기", nav: "작업 공간", theme: "다크", textSize: "글자 크기" };
      await expect(page.getByRole("link", { name: structuralCopy.skip })).toHaveCount(1);
      await expect(page.getByRole("navigation", { name: structuralCopy.nav })).toBeVisible();
      await expect(page.getByRole("button", { name: structuralCopy.theme })).toBeVisible();
      await expect(page.getByRole("group", { name: structuralCopy.textSize })).toBeVisible();
    }
    if (region === "kr") {
      await expect(
        page.getByText("The central bank held its benchmark rate and signalled patience on cuts."),
      ).toHaveAttribute("lang", "en");
    }
    await expectAccessibleViewport(page, 1280, 720);
    await expectAccessibleViewport(page, 390, 844);
    await expectAccessibleViewport(page, 720, 900);
  });
}

test("brief workspace is accessible at desktop, mobile and zoom-equivalent widths", async ({ page }) => {
  await useReturningReader(page);
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.goto("/brief");
  await expectAccessibleViewport(page, 1280, 720);
  await expectAccessibleViewport(page, 390, 844);
  await expectAccessibleViewport(page, 720, 900);
});
