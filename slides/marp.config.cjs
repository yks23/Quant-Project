const path = require("node:path");

module.exports = {
  themeSet: path.join(__dirname, "theme/lecture.css"),
  html: true,
  allowLocalFiles: true,
  lang: "zh-CN",
  pdfOutlines: { pages: false, headings: true },
  options: { math: "mathjax" },
};
