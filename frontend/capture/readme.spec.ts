import { resolve } from "node:path";
import { expect, test, type Page } from "@playwright/test";

const SCREENSHOTS = resolve(process.cwd(), "../docs/screenshots");

async function prepare(page: Page) {
  await page.addInitScript(() => {
    localStorage.setItem("cmb-onboarding-v1", "done");
    localStorage.setItem("cmb-theme", "light");
    localStorage.setItem("cmb-text-size", "normal");
  });
}

async function settle(page: Page) {
  await expect(page.getByTestId("data-provenance")).toBeVisible();
  await page.evaluate(() => document.fonts.ready);
}

test("captures the verified local demo for the README", async ({ page }) => {
  await prepare(page);

  for (const capture of [
    { path: "/?region=uk", file: "radar-uk.png", heading: "Morning Market Radar" },
    { path: "/?region=kr", file: "radar-korea.png", heading: "모닝 마켓 레이더" },
    { path: "/?region=tw", file: "radar-taiwan.png", heading: "早晨市場雷達" },
  ]) {
    await page.goto(capture.path);
    await settle(page);
    await expect(page.getByText(capture.heading, { exact: true }).first()).toBeVisible();
    await page.screenshot({
      path: resolve(SCREENSHOTS, capture.file),
      fullPage: false,
      animations: "disabled",
    });
  }

  await page.goto("/brief");
  await expect(page.getByRole("heading", { name: "Evidence-backed company brief" })).toBeVisible();
  await page.evaluate(() => document.fonts.ready);
  await page.screenshot({
    path: resolve(SCREENSHOTS, "brief-workspace.png"),
    fullPage: false,
    animations: "disabled",
  });

  await page.goto("/?region=tw");
  await settle(page);
  const news = page.getByRole("heading", { name: "市場新聞" }).locator("xpath=ancestor::section[1]");
  await expect(news).toBeVisible();
  await news.screenshot({
    path: resolve(SCREENSHOTS, "news-taiwan.png"),
    animations: "disabled",
  });
});
