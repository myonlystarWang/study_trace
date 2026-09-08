# 微信测试号双向交互引擎实施计划 (WeChat Interactive Inbound Engine)

基于用户确认的 [doc/wechat_interactive_agent_plan.md](file:///d:/工作/ww/personal_work/study_trace/doc/wechat_interactive_agent_plan.md) 方案，实施微信公众号测试号（Sandbox）双向互动链路，支持家长在微信聊天框直接打字录入作业、勾选打卡、查询今日作业与进度，并在满卡时自动全家广播。

---

## 一、 微信测试号页面填写指导 (必看前置)

在微信测试号后台管理页面（`https://mp.weixin.qq.com/debug/cgi-bin/sandbox`），找到 **「接口配置信息」**（位于“测试号二维码”下方）：

> [!IMPORTANT]
> **关于微信后台“配置失败”的关键机制**：  
> 当您在微信后台点击「提交」时，微信官方服务器会**立即以 GET 请求访问填写的 URL** 进行签名校验。若服务器未就绪或无法在 5 秒内返回匹配的 `echostr`，微信后台会直接红字报错“配置失败”。  
> **因此，我们将优先在阶段 1 把验签接口部署就绪，届时您直接点击「提交」即可 100% 成功。**

### 填写参数明细表：
| 配置项 | 微信后台对应输入框 | 填写具体内容 | 说明 |
| :--- | :--- | :--- | :--- |
| **URL** | `URL` | `https://study.raddishlab.tech/api/wechat/callback` | 我们已绑定的 Cloudflare 公网固定安全域名 |
| **Token** | `Token` | `studytrace2026` | 用于微信 SHA1 签名校验的加密令牌（系统将在 `.env` 中保存） |

---

## 二、 核心架构与拟修改/新增文件

### 1. 架构模块拆分
```
backend/app/
├── routers/
│   └── wechat.py              # [NEW] 微信 Webhook 回调路由 (GET 握手鉴权 + POST 消息接收)
├── utils/
│   └── wechat_intent.py       # [NEW] 微信双模意图解析器与动作分发器 (打卡/新增/查询/满卡联动)
├── config.py                  # [MODIFY] 增加 WECHAT_CALLBACK_TOKEN 配置项
├── main.py                    # [MODIFY] 挂载 wechat.py 路由至 /api/wechat
└── tests/
    └── test_wechat_inbound.py # [NEW] 微信上行指令解析与防重自动化测试套件
```

---

## 三、 详细实施步骤

### 阶段 1：环境配置与 Webhook 验签接口 (让微信后台配置成功)
1. 在 [backend/app/config.py](file:///d:/工作/ww/personal_work/study_trace/backend/app/config.py) 中增加 `WECHAT_CALLBACK_TOKEN: str = "studytrace2026"`，同步注入 `.env` 与 `data/.env`。
2. 新建 [backend/app/routers/wechat.py](file:///d:/工作/ww/personal_work/study_trace/backend/app/routers/wechat.py)：
   - 实现 `GET /api/wechat/callback`：提取 `signature`, `timestamp`, `nonce`, `echostr`，以字典序排序并做 `sha1` 散列对比。对比成功后直接以 `text/plain` 响应 `echostr`。
3. 在 [backend/app/main.py](file:///d:/工作/ww/personal_work/study_trace/backend/app/main.py) 中挂载该路由。
4. **【用户验证节点】**：通知用户在微信测试号后台填入上述 URL 与 Token，点击「提交」验证握手成功。

### 阶段 2：意图解析引擎与指令识别
新建 [backend/app/utils/wechat_intent.py](file:///d:/工作/ww/personal_work/study_trace/backend/app/utils/wechat_intent.py)：
1. **白名单校验**：比对发送者的 OpenID 是否属于已在系统登记的家庭成员（妈妈、爸爸等），未授权者回复友好指引。
2. **意图匹配与动作提取**：
   - **打卡意图**：匹配学科关键词（支持 7 科及动态学科）+ 动词（`完成`、`做完了`、`搞定`、`打卡`、`写完`）。
   - **新增作业意图**：匹配 `新增作业/添加作业/留作业` + 学科 + 题干内容。
   - **查询今日作业意图**：匹配 `今日作业/作业清单/还有什么作业/作业`。
   - **查询进度意图**：匹配 `进度/打卡天数/连续打卡/streak`。
   - **帮助指引**：匹配 `帮助/?/功能`。
3. **XML 被动回复生成**：格式化为微信合规的 `<xml>` 文本消息。

### 阶段 3：数据库状态更新与关键满卡全家广播联动
1. 优化业务写操作：
   - 当收到打卡指令，更新数据库中该学生今日该科目的未完成条目为 `is_completed=True`，并记录 `completed_at`。
   - 重新统计今日全部作业项。
2. **满卡联动**：
   - 若本次打卡导致今日全部作业 100% 达成，后端异步唤起 `send_wechat_sandbox`，向全家多成员自动广播发送「🎉 今日作业满卡喜报！」。

### 阶段 4：自动化测试与端到端演练
1. 编写 [tests/test_wechat_inbound.py](file:///d:/工作/ww/personal_work/study_trace/tests/test_wechat_inbound.py)：
   - 验证握手验签成功与伪造签名 403 拦截；
   - 验证口语化指令（“数学 做完了”、“打卡 英语”）打卡成功；
   - 验证新增作业指令成功创建条目；
   - 验证未授权陌生 OpenID 拦截；
   - 验证微信 5 秒重试 `MsgId` 防重幂等。
2. 运行全量测试套件保证零回归，重启生产服务并在真机微信实测。

---

## 四、 验证计划

### 自动化验证
```powershell
uv run pytest tests/test_wechat_inbound.py -v
uv run pytest tests/test_m3_notifications_and_calendar.py -v
```

### 真机手动交互演练
1. 在微信测试号聊天框发送：`今日作业`，应立即收到今日作业清单与完成进度；
2. 发送：`数学 完成`，应立即收到打卡确认，且系统作业列表自动变为打勾；
3. 发送：`新增作业 英语 背诵Unit3单词`，系统应成功新增该作业条目。
