# LuaS30 IDE — Wiki

Tài liệu wiki song ngữ **Tiếng Việt / English** cho LuaS30 IDE.

Bilingual **Vietnamese / English** wiki for LuaS30 IDE.

## Cấu trúc / Layout

```text
wiki/
├── README.md          bạn đang ở đây / you are here
├── vi/                Tiếng Việt
│   ├── Home.md
│   ├── Getting-Started.md
│   ├── Studio-UI.md
│   ├── Building-VXP.md
│   ├── Project-Structure.md
│   ├── AI-Agent.md
│   ├── Troubleshooting.md
│   └── FAQ.md
└── en/                English
    ├── Home.md
    ├── Getting-Started.md
    ├── Studio-UI.md
    ├── Building-VXP.md
    ├── Project-Structure.md
    ├── AI-Agent.md
    ├── Troubleshooting.md
    └── FAQ.md
```

Hai thư mục có **cùng tên file**. Trang `vi/Home.md` tương ứng 1-1 với
`en/Home.md`, nên khi sửa một trang chỉ cần sửa đúng file cùng tên ở thư mục còn
lại. Mỗi trang có dòng chuyển ngữ ngay dưới tiêu đề.

Both folders use **identical file names**. `vi/Home.md` maps 1-1 to
`en/Home.md`, so a change to one page only needs the same-named file in the other
folder. Every page carries a language switcher directly under its title.

## Wiki này khác gì `doc/`?

`doc/` là **nguồn sự thật sâu** — changelog theo phiên bản, validation report,
kiến trúc, SDK, quy tắc kỹ thuật dài.

`wiki/` là **cửa vào** — giải thích đủ để bắt đầu và tra cứu nhanh, rồi trỏ sang
trang `doc/` tương ứng khi cần chi tiết. Khi hai nơi khác nhau, `doc/` và source
code là bên đúng.

`doc/` is the **authoritative deep reference** — per-version changelogs, validation
reports, architecture, SDK and long-form engineering rules.

`wiki/` is the **entry point** — enough to get started and look things up fast, then
linking to the matching `doc/` page for detail. Where the two disagree, `doc/` and
the source code win.

## Commit lên GitHub / Committing to GitHub

Wiki này là thư mục markdown thường, commit trực tiếp vào repo:

```bat
git add wiki
git commit -m "docs: add bilingual wiki"
git push
```

GitHub render markdown trong repo, và link tương đối giữa các trang hoạt động
bình thường khi duyệt trên web.

Nếu muốn dùng như **GitHub Wiki** (`https://github.com/<user>/<repo>/wiki`):

1. clone wiki repo: `git clone https://github.com/<user>/<repo>.wiki.git`;
2. copy nội dung của **một** ngôn ngữ vào gốc (GitHub Wiki cần `Home.md` ở gốc);
3. push.

```bat
git clone https://github.com/<user>/<repo>.wiki.git
xcopy /E /I wiki\vi\* repo.wiki\
cd repo.wiki && git add -A && git commit -m "wiki: initial" && git push
```

Đổi `wiki\vi\` thành `wiki\en\` nếu muốn wiki mặc định là tiếng Anh.

This wiki is ordinary markdown, commit it straight into the repo. GitHub renders
repo markdown and relative links work while browsing. To use it as a **GitHub
Wiki** instead, clone the `.wiki.git` repository and copy the contents of **one**
language into its root (GitHub Wiki requires `Home.md` at the root), then push.

## Bản quyền / License

© Qeafivels All rights reserved. — <https://qeafivels.com/>

Xem [`LICENSE`](../LICENSE). Thành phần bên thứ ba có giấy phép riêng, xem
[`doc/legal/THIRD_PARTY_NOTICES.md`](../doc/legal/THIRD_PARTY_NOTICES.md).
