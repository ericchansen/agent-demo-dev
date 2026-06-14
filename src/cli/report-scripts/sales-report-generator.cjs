#!/usr/bin/env node
/**
 * Sales Analysis Report Generator — produces multi-tab Excel workbook.
 *
 * Usage:
 *   node sales-report-generator.cjs <input.json> [output.xlsx]
 *
 * Input: JSON file conforming to schemas/sales-analysis-output.json
 * Output: Excel workbook with Summary, Pipeline, Quota, Research, Activity tabs
 *
 * Dependencies: exceljs (install via `npm install exceljs` in this directory)
 */

const ExcelJS = require("exceljs");
const fs = require("fs");
const path = require("path");

// ---------------------------------------------------------------------------
// Color palette
// ---------------------------------------------------------------------------
const COLORS = {
  header: "1F4E79",
  headerFont: "FFFFFF",
  green: "C6EFCE",
  greenFont: "006100",
  yellow: "FFEB9C",
  yellowFont: "9C5700",
  red: "FFC7CE",
  redFont: "9C0006",
  altRow: "F2F7FB",
  border: "D9E2F3",
};

function riskFill(rating) {
  switch ((rating || "").toLowerCase()) {
    case "green":
      return { type: "pattern", pattern: "solid", fgColor: { argb: COLORS.green } };
    case "yellow":
      return { type: "pattern", pattern: "solid", fgColor: { argb: COLORS.yellow } };
    case "red":
      return { type: "pattern", pattern: "solid", fgColor: { argb: COLORS.red } };
    default:
      return undefined;
  }
}

function riskFont(rating) {
  switch ((rating || "").toLowerCase()) {
    case "green":
      return { color: { argb: COLORS.greenFont }, bold: true };
    case "yellow":
      return { color: { argb: COLORS.yellowFont }, bold: true };
    case "red":
      return { color: { argb: COLORS.redFont }, bold: true };
    default:
      return {};
  }
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------
function styleHeader(row) {
  row.eachCell((cell) => {
    cell.fill = { type: "pattern", pattern: "solid", fgColor: { argb: COLORS.header } };
    cell.font = { color: { argb: COLORS.headerFont }, bold: true, size: 11 };
    cell.alignment = { vertical: "middle", horizontal: "center" };
  });
  row.height = 24;
}

function addAltRowShading(sheet, startRow) {
  for (let i = startRow; i <= sheet.rowCount; i++) {
    if ((i - startRow) % 2 === 1) {
      sheet.getRow(i).eachCell((cell) => {
        cell.fill = { type: "pattern", pattern: "solid", fgColor: { argb: COLORS.altRow } };
      });
    }
  }
}

function usd(val) {
  return typeof val === "number" ? val : 0;
}

// ---------------------------------------------------------------------------
// Tab builders
// ---------------------------------------------------------------------------
function buildSummaryTab(wb, data) {
  const ws = wb.addWorksheet("Summary");
  const meta = data.metadata || {};
  const summary = data.summary || {};
  const quota = data.quota || {};

  ws.columns = [{ width: 30 }, { width: 25 }, { width: 20 }, { width: 20 }];

  // Title
  ws.mergeCells("A1:D1");
  const titleCell = ws.getCell("A1");
  titleCell.value = `Sales Analysis: ${meta.customer_name || "N/A"}`;
  titleCell.font = { size: 16, bold: true, color: { argb: COLORS.header } };
  titleCell.alignment = { horizontal: "left" };

  ws.getCell("A2").value = `Generated: ${meta.generated_at || new Date().toISOString()}`;
  ws.getCell("A2").font = { italic: true, color: { argb: "808080" } };

  // KPI cards (row 4+)
  const kpis = [
    ["YTD Revenue", usd(summary.total_revenue_ytd), "$#,##0"],
    ["Prior Year Revenue", usd(summary.total_revenue_prior_year), "$#,##0"],
    ["YoY Growth", (summary.yoy_growth_pct || 0) / 100, "0.0%"],
    ["Annual Target", usd(quota.annual_target), "$#,##0"],
    ["Quota Attainment", (quota.attainment_pct || 0) / 100, "0.0%"],
    ["Pipeline Coverage", quota.pipeline_coverage || 0, "0.0x"],
    ["Run Rate Projection", usd(quota.run_rate_projection), "$#,##0"],
    ["Risk Rating", quota.risk_rating || "N/A", null],
  ];

  const headerRow = ws.addRow(["Metric", "Value"]);
  styleHeader(headerRow);

  kpis.forEach(([label, value, fmt]) => {
    const row = ws.addRow([label, value]);
    if (fmt) row.getCell(2).numFmt = fmt;
    if (label === "Risk Rating") {
      const fill = riskFill(value);
      const font = riskFont(value);
      if (fill) row.getCell(2).fill = fill;
      if (font) row.getCell(2).font = font;
    }
  });

  // Executive summary
  if (summary.executive_summary) {
    const r = ws.rowCount + 2;
    ws.mergeCells(`A${r}:D${r}`);
    ws.getCell(`A${r}`).value = "Executive Summary";
    ws.getCell(`A${r}`).font = { size: 13, bold: true };
    ws.mergeCells(`A${r + 1}:D${r + 3}`);
    ws.getCell(`A${r + 1}`).value = summary.executive_summary;
    ws.getCell(`A${r + 1}`).alignment = { wrapText: true, vertical: "top" };
  }
}

function buildPipelineTab(wb, data) {
  const ws = wb.addWorksheet("Pipeline");
  // Support both array format and object-with-customers format
  const rawPipeline = data.pipeline || [];
  const pipeline = Array.isArray(rawPipeline)
    ? rawPipeline
    : rawPipeline.customers || [];

  ws.columns = [
    { header: "Deal / Customer", width: 30 },
    { header: "Revenue", width: 15 },
    { header: "Orders", width: 12 },
    { header: "Stage", width: 18 },
    { header: "Close Date", width: 14 },
    { header: "Territory", width: 16 },
    { header: "Rep", width: 18 },
  ];
  styleHeader(ws.getRow(1));

  pipeline.forEach((deal) => {
    const row = ws.addRow([
      deal.deal_name || deal.name || deal.customer || "",
      usd(deal.value || deal.revenue || 0),
      deal.orders || "",
      deal.stage || "",
      deal.close_date || "",
      deal.territory || "",
      deal.rep || "",
    ]);
    row.getCell(2).numFmt = "$#,##0";
  });

  // Total row
  if (pipeline.length > 0) {
    const total = pipeline.reduce((s, d) => s + usd(d.value || d.revenue || 0), 0);
    const totalRow = ws.addRow(["TOTAL", total, "", "", "", "", ""]);
    totalRow.getCell(1).font = { bold: true };
    totalRow.getCell(2).font = { bold: true };
    totalRow.getCell(2).numFmt = "$#,##0";
  }

  addAltRowShading(ws, 2);
}

function buildQuotaTab(wb, data) {
  const ws = wb.addWorksheet("Quota");
  const quota = data.quota || {};
  const cats = quota.by_category || [];

  ws.columns = [
    { header: "Category", width: 28 },
    { header: "Current FY Revenue", width: 20 },
    { header: "Growth Rate", width: 14 },
    { header: "Projected FY Revenue", width: 22 },
  ];
  styleHeader(ws.getRow(1));

  cats.forEach((cat) => {
    const row = ws.addRow([
      cat.category,
      usd(cat.current_fy_revenue),
      cat.growth_rate || 0,
      usd(cat.projected_fy_revenue),
    ]);
    row.getCell(2).numFmt = "$#,##0";
    row.getCell(3).numFmt = "0.0%";
    row.getCell(4).numFmt = "$#,##0";
  });

  // Monthly trend below
  const trend = quota.monthly_trend || [];
  if (trend.length > 0) {
    const startRow = ws.rowCount + 3;
    ws.getCell(`A${startRow - 1}`).value = "Monthly Revenue Trend";
    ws.getCell(`A${startRow - 1}`).font = { size: 13, bold: true };

    const trendHeader = ws.getRow(startRow);
    trendHeader.values = ["Month", "Revenue", "Target"];
    styleHeader(trendHeader);

    trend.forEach((m) => {
      const row = ws.addRow([m.month, usd(m.revenue), usd(m.target)]);
      row.getCell(2).numFmt = "$#,##0";
      row.getCell(3).numFmt = "$#,##0";
    });
  }

  addAltRowShading(ws, 2);
}

function buildResearchTab(wb, data) {
  const ws = wb.addWorksheet("Research");
  const research = data.research || {};

  ws.columns = [
    { header: "Title", width: 35 },
    { header: "Source", width: 18 },
    { header: "Date", width: 12 },
    { header: "Snippet", width: 45 },
    { header: "Sales Implication", width: 35 },
  ];
  styleHeader(ws.getRow(1));

  (research.findings || []).forEach((f) => {
    const row = ws.addRow([
      f.title || "",
      f.source || "",
      f.date || "",
      f.snippet || "",
      f.sales_implication || "",
    ]);
    row.getCell(4).alignment = { wrapText: true };
    row.getCell(5).alignment = { wrapText: true };
  });

  // Tailwinds / Headwinds
  const startRow = ws.rowCount + 3;
  ws.getCell(`A${startRow - 1}`).value = "Market Factors";
  ws.getCell(`A${startRow - 1}`).font = { size: 13, bold: true };

  (research.tailwinds || []).forEach((t) => {
    const row = ws.addRow(["▲ Tailwind", t]);
    row.getCell(1).font = { color: { argb: COLORS.greenFont }, bold: true };
  });
  (research.headwinds || []).forEach((h) => {
    const row = ws.addRow(["▼ Headwind", h]);
    row.getCell(1).font = { color: { argb: COLORS.redFont }, bold: true };
  });

  addAltRowShading(ws, 2);
}

function buildActivityTab(wb, data) {
  const ws = wb.addWorksheet("Activity");
  const activity = data.activity || {};

  ws.columns = [{ width: 28 }, { width: 25 }];

  ws.mergeCells("A1:B1");
  ws.getCell("A1").value = "Engagement Summary";
  ws.getCell("A1").font = { size: 14, bold: true, color: { argb: COLORS.header } };

  const metrics = [
    ["Engagement Score", activity.engagement_score],
    ["Meetings (last 30d)", activity.meetings_last_30d],
    ["Emails (last 30d)", activity.emails_last_30d],
    ["Last Meeting", activity.last_meeting_date || "N/A"],
    ["Last Email", activity.last_email_date || "N/A"],
    ["Relationship Strength", activity.relationship_strength || "N/A"],
  ];

  metrics.forEach(([label, value]) => {
    ws.addRow([label, value]);
  });

  // Key contacts
  const contacts = activity.key_contacts || [];
  if (contacts.length > 0) {
    const startRow = ws.rowCount + 2;
    ws.getCell(`A${startRow}`).value = "Key Contacts";
    ws.getCell(`A${startRow}`).font = { size: 13, bold: true };

    ws.columns = [{ width: 28 }, { width: 25 }, { width: 16 }, { width: 14 }];
    const hdr = ws.getRow(startRow + 1);
    hdr.values = ["Name", "Role", "Last Interaction", "# Interactions"];
    styleHeader(hdr);

    contacts.forEach((c) => {
      ws.addRow([c.name, c.role, c.last_interaction || "", c.interaction_count || 0]);
    });
  }
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------
async function main() {
  const args = process.argv.slice(2);
  if (args.length < 1) {
    console.error("Usage: node sales-report-generator.cjs <input.json> [output.xlsx]");
    process.exit(1);
  }

  const inputPath = path.resolve(args[0]);
  const data = JSON.parse(fs.readFileSync(inputPath, "utf-8"));
  const customerSlug = (data.metadata?.customer_name || "report").replace(/\s+/g, "_");
  const dateSlug = new Date().toISOString().slice(0, 10);
  const outputPath = args[1]
    ? path.resolve(args[1])
    : path.resolve(`Sales_Analysis_${customerSlug}_${dateSlug}.xlsx`);

  const wb = new ExcelJS.Workbook();
  wb.creator = "Fabric Sales Agent Accelerator";
  wb.created = new Date();

  buildSummaryTab(wb, data);
  buildPipelineTab(wb, data);
  buildQuotaTab(wb, data);
  buildResearchTab(wb, data);
  buildActivityTab(wb, data);

  await wb.xlsx.writeFile(outputPath);
  console.log(`✅ Report saved: ${outputPath}`);
}

main().catch((err) => {
  console.error("❌ Report generation failed:", err.message);
  process.exit(1);
});
