# TicketMaster Vendor Plugin

自包含的 TicketMaster 票務 vendor plugin。

實作雙重合約：
- **Plugin ABC**（`platform-plugin-sdk`）：生命週期（start/stop/health）
- **VendorProxy ABC**（`unified-ticket-api`）：業務方法（search/orders/inventory）

作為 git submodule 整合進 [ticket-vendor](https://github.com/shawnlin0125/ticket-vendor) meta-repo。

## 結構

```
├── plugin.py          ← TicketmasterPlugin（雙 ABC 實作）
├── mock/
│   ├── vendor/        ← Downstream: 模擬 TicketMaster API
│   └── business/      ← Upstream: 模擬業務系統呼叫
├── fixtures/          ← 測試資料
├── schema/            ← DB migrations
└── tests/             ← 合約/模擬/邊界測試
```

## 開發

```bash
# 安裝依賴
pip install git+https://github.com/shawnlin0125/plugin-hub.git@go-rewrite#subdirectory=platform-plugin-sdk
pip install git+https://github.com/shawnlin0125/ticket-vendor.git#subdirectory=unified-ticket-api
pip install -e ".[dev]"

# 跑測試
pytest tests/ -v
```

## Release Cycle

獨立於其他 vendor。每個 vendor repo 有自己的 release cycle。

```
feature → PR → CI pass → merge main → tag v0.X.0
                                        ↓
                              ticket-vendor meta-repo 更新 submodule pointer
```
