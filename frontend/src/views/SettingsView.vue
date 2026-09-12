<template>
  <div class="settings-view">
    <van-nav-bar title="家长管理" fixed placeholder />

    <div class="settings-container">
      <!-- 门禁口令验证卡片 -->
      <div class="st-card pin-gate-card" v-if="!isUnlocked">
        <div class="gate-icon-circle">
          <van-icon name="lock" size="32" color="#d97706" />
        </div>
        <h3>家长模式身份验证</h3>
        <p class="gate-tip">初中生专注模式已开启。请输入管理口令进入：</p>
        
        <van-field
          v-model="inputPin"
          type="password"
          maxlength="6"
          placeholder="请输入 6 位管理口令 (默认 888888)"
          class="pin-field"
          center
        />

        <van-button
          type="primary"
          block
          round
          :loading="verifying"
          @click="handleVerifyPin"
          style="margin-top: 1.5rem;"
        >
          解锁进入管理视图
        </van-button>
      </div>

      <!-- 解锁后的家长管理功能 -->
      <div class="unlocked-content" v-else>
        <van-notice-bar
          left-icon="info-o"
          text="已进入家长管理空间，可配置提醒渠道、管理学科分值及全站备份。"
          class="settings-top-notice"
        />

        <!-- 常驻顶部：月度出勤核心看板与快捷操作 -->
        <div class="st-card overview-dashboard-card">
          <div class="overview-card-header">
            <div class="overview-title-group">
              <span class="st-icon-badge st-icon-badge--info">
                <van-icon name="chart-trending-o" />
              </span>
              <span class="overview-title">出勤核心看板</span>
            </div>
            <div class="month-stepper">
              <van-button size="mini" icon="arrow-left" @click="changeMonth(-1)" />
              <span class="current-month-text">{{ currentYear }} 年 {{ currentMonth }} 月</span>
              <van-button size="mini" icon="arrow" @click="changeMonth(1)" />
            </div>
          </div>

          <!-- 月度核心指标网格 -->
          <div class="monthly-stats-grid">
            <div class="monthly-stat-item">
              <div class="m-stat-val text-primary">{{ monthlyData?.average_completion_rate ?? '--' }}%</div>
              <div class="m-stat-label">月均打卡率</div>
            </div>
            <div class="monthly-stat-item">
              <div class="m-stat-val">{{ monthlyData?.recorded_days ?? 0 }} / {{ monthlyData?.total_days ?? 0 }}</div>
              <div class="m-stat-label">有效打卡天数</div>
            </div>
            <div class="monthly-stat-item">
              <div class="m-stat-val text-succ">{{ monthlyData?.perfect_days ?? 0 }} 天</div>
              <div class="m-stat-label">全满卡天数</div>
            </div>
          </div>

          <!-- 快捷操作：发送今日汇总 -->
          <div class="overview-quick-actions">
            <van-button
              type="warning"
              plain
              round
              size="small"
              icon="guide-o"
              class="quick-summary-btn"
              :loading="sendingSummary"
              @click="handleSendSummaryNow"
            >
              一键发送今日作业汇总快报
            </van-button>
          </div>
        </div>

        <!-- 分类控制工具栏 -->
        <div class="section-toolbar">
          <div class="section-toolbar-left">
            <span class="section-toolbar-title">系统管理与设置</span>
            <span class="section-toolbar-count">6 项</span>
          </div>
          <button class="section-toggle-all-btn" @click="toggleAllSections">
            <van-icon :name="areAllExpanded ? 'arrow-up' : 'arrow-down'" />
            <span>{{ areAllExpanded ? '全部收起' : '全部展开' }}</span>
          </button>
        </div>

        <!-- 卡片 1: 每日提醒与多渠道推送设置 (可折叠) -->
        <div class="st-card st-collapse-card" :class="{ 'is-open': isSectionOpen('notif') }">
          <div class="st-collapse-header" @click="toggleSection('notif')">
            <div class="st-collapse-header-left">
              <span class="st-icon-badge st-icon-badge--primary">
                <van-icon name="volume-o" />
              </span>
              <div class="st-collapse-title-group">
                <span class="st-collapse-title">推送提醒设置</span>
                <span class="st-collapse-summary">{{ notifSummaryText }}</span>
              </div>
            </div>
            <div class="st-collapse-header-right">
              <van-icon name="arrow-down" class="st-collapse-arrow" />
            </div>
          </div>

          <div class="st-collapse-body" v-show="isSectionOpen('notif')">
            <!-- 时段说明 -->
            <van-cell
              title="提醒策略"
              label="20:10 / 21:10 中途催办 (100%完成自动跳过免打扰) ｜ 21:50 晚间汇总日报 (满卡送达喜报)"
            />

            <!-- 启用渠道选择区 (2列响应式卡片网格，彻底释放水平空间) -->
            <div class="channel-selector-section">
              <div class="channel-selector-header">
                <span class="selector-title">启用推送渠道（多选）</span>
                <span class="selector-count" v-if="notifConfig.enabled_channels.length > 0">
                  已启用 {{ notifConfig.enabled_channels.length }} 个渠道
                </span>
                <span class="selector-count-empty" v-else>
                  未启用任何渠道
                </span>
              </div>
              <van-checkbox-group v-model="notifConfig.enabled_channels" class="channel-grid">
                <div
                  class="channel-select-card"
                  :class="{ 'is-active': notifConfig.enabled_channels.includes('wechat_sandbox') }"
                  @click="toggleChannel('wechat_sandbox')"
                >
                  <van-checkbox name="wechat_sandbox" shape="square" @click.stop />
                  <span class="st-icon-badge st-icon-badge--success channel-badge">
                    <van-icon name="chat-o" />
                  </span>
                  <span class="channel-card-text">微信测试号</span>
                </div>

                <div
                  class="channel-select-card"
                  :class="{ 'is-active': notifConfig.enabled_channels.includes('serverchan') }"
                  @click="toggleChannel('serverchan')"
                >
                  <van-checkbox name="serverchan" shape="square" @click.stop />
                  <span class="st-icon-badge st-icon-badge--warning channel-badge">
                    <van-icon name="comment-o" />
                  </span>
                  <span class="channel-card-text">Server酱</span>
                </div>

                <div
                  class="channel-select-card"
                  :class="{ 'is-active': notifConfig.enabled_channels.includes('bark') }"
                  @click="toggleChannel('bark')"
                >
                  <van-checkbox name="bark" shape="square" @click.stop />
                  <span class="st-icon-badge st-icon-badge--purple channel-badge">
                    <van-icon name="phone-o" />
                  </span>
                  <span class="channel-card-text">iOS Bark</span>
                </div>

                <div
                  class="channel-select-card"
                  :class="{ 'is-active': notifConfig.enabled_channels.includes('webhook') }"
                  @click="toggleChannel('webhook')"
                >
                  <van-checkbox name="webhook" shape="square" @click.stop />
                  <span class="st-icon-badge st-icon-badge--neutral channel-badge">
                    <van-icon name="cluster-o" />
                  </span>
                  <span class="channel-card-text">群机器人</span>
                </div>
              </van-checkbox-group>
            </div>

            <!-- 未启用渠道时的友好提示 -->
            <div class="channel-empty-tip" v-if="notifConfig.enabled_channels.length === 0">
              <van-icon name="info-o" />
              <span>请在上方勾选需要启用的渠道，系统将展开对应配置项</span>
            </div>

            <!-- 微信官方测试号配置 (Sandbox) -->
            <div class="channel-config-box" v-if="notifConfig.enabled_channels.includes('wechat_sandbox')">
              <div class="channel-header">
                <div class="channel-header-left">
                  <span class="st-icon-badge st-icon-badge--success">
                    <van-icon name="chat-o" />
                  </span>
                  <span class="channel-title">微信测试号</span>
                </div>
                <span class="st-status-tag st-status-tag--success">免费10万次/天</span>
              </div>
              <van-field
                v-model="notifConfig.wechat_app_id"
                label="AppID"
                label-width="85px"
                center
                class="channel-field"
                placeholder="测试号 AppID (wx...)"
              />
              <van-field
                v-model="notifConfig.wechat_app_secret"
                label="Secret"
                label-width="85px"
                type="password"
                center
                class="channel-field"
                placeholder="测试号 AppSecret"
              />
              <van-field
                v-model="notifConfig.wechat_template_id"
                label="模板ID"
                label-width="85px"
                center
                class="channel-field"
                placeholder="消息模板 ID"
              />
              <!-- 结构化家庭成员接收人列表 -->
              <div class="wechat-members-section">
                <div class="wechat-members-header">
                  <span class="wechat-members-title">
                    <van-icon name="friends-o" />
                    家庭成员接收列表 ({{ wechatMemberList.length }}人)
                  </span>
                  <van-button
                    size="mini"
                    type="primary"
                    plain
                    class="channel-test-btn"
                    :loading="testingChannel === 'wechat_sandbox'"
                    @click="handleTestChannel('wechat_sandbox', {
                      target: serializeWechatMembers(),
                      app_id: notifConfig.wechat_app_id,
                      app_secret: notifConfig.wechat_app_secret,
                      template_id: notifConfig.wechat_template_id
                    })"
                  >
                    全员广播测试
                  </van-button>
                </div>

                <div class="wechat-member-card" v-for="(m, idx) in wechatMemberList" :key="idx">
                  <div class="wechat-member-row-top">
                    <div class="wechat-member-identity">
                      <span class="member-index-badge">#{{ idx + 1 }}</span>
                      <input
                        v-model="m.name"
                        class="member-name-input"
                        placeholder="称谓 (如 爸爸/妈妈)"
                      />
                    </div>
                    <div class="wechat-member-actions">
                      <van-button
                        size="mini"
                        type="default"
                        class="member-single-test-btn"
                        :loading="testingChannel === `wechat_single_${idx}`"
                        @click="testSingleMember(m, idx)"
                      >
                        单人测试
                      </van-button>
                      <van-icon
                        name="delete-o"
                        class="member-del-btn"
                        v-if="wechatMemberList.length > 1"
                        @click="removeWechatMember(idx)"
                      />
                    </div>
                  </div>
                  <div class="wechat-member-openid-box">
                    <input
                      v-model="m.openid"
                      class="member-openid-input"
                      placeholder="请输入微信 OpenID (以 oz1n... 开头)"
                    />
                  </div>
                </div>

                <div class="wechat-add-member-wrapper">
                  <van-button
                    size="small"
                    type="primary"
                    plain
                    icon="plus"
                    block
                    class="wechat-add-btn"
                    @click="addWechatMember"
                  >
                    添加家庭成员 OpenID
                  </van-button>
                </div>
              </div>
              <div class="channel-caption">
                <van-icon name="info-o" class="caption-icon" />
                <span>直连微信官方服务器；扫测试号二维码关注后，将 OpenID 填入上方并备注，即可同步弹窗接收。</span>
              </div>
            </div>

            <!-- Server酱 配置 (按需展示) -->
            <div class="channel-config-box" v-if="notifConfig.enabled_channels.includes('serverchan')">
              <div class="channel-header">
                <div class="channel-header-left">
                  <span class="st-icon-badge st-icon-badge--warning">
                    <van-icon name="comment-o" />
                  </span>
                  <span class="channel-title">Server酱 (Turbo版)</span>
                </div>
                <span class="st-status-tag st-status-tag--warning">免费 5条/天</span>
              </div>
              <van-field
                v-model="notifConfig.serverchan_key"
                label="SendKey"
                label-width="70px"
                center
                class="channel-field"
                placeholder="Server酱的 SCT SendKey"
              >
                <template #button>
                  <van-button
                    size="small"
                    type="default"
                    class="channel-test-btn"
                    :loading="testingChannel === 'serverchan'"
                    @click="handleTestChannel('serverchan', notifConfig.serverchan_key)"
                  >
                    测试
                  </van-button>
                </template>
              </van-field>
            </div>

            <!-- iOS Bark 配置 (按需展示) -->
            <div class="channel-config-box" v-if="notifConfig.enabled_channels.includes('bark')">
              <div class="channel-header">
                <div class="channel-header-left">
                  <span class="st-icon-badge st-icon-badge--purple">
                    <van-icon name="phone-o" />
                  </span>
                  <span class="channel-title">iOS Bark 推送</span>
                </div>
                <span class="st-status-tag st-status-tag--purple">iPhone 首选 · 免账号</span>
              </div>
              <van-field
                v-model="notifConfig.bark_key"
                label="Bark Key"
                label-width="70px"
                center
                class="channel-field"
                placeholder="Bark App 中的设备 Key 或完整 URL"
              >
                <template #button>
                  <van-button
                    size="small"
                    type="default"
                    class="channel-test-btn"
                    :loading="testingChannel === 'bark'"
                    @click="handleTestChannel('bark', notifConfig.bark_key)"
                  >
                    测试
                  </van-button>
                </template>
              </van-field>
              <div class="channel-caption">
                <van-icon name="info-o" class="caption-icon" />
                <span>支持多台 iPhone：在不同手机安装 Bark 后，将多个 Key 用逗号隔开，全家手机即可同时秒级收到锁屏通知。</span>
              </div>
            </div>

            <!-- 群机器人 Webhook (按需展示) -->
            <div class="channel-config-box" v-if="notifConfig.enabled_channels.includes('webhook')">
              <div class="channel-header">
                <div class="channel-header-left">
                  <span class="st-icon-badge st-icon-badge--neutral">
                    <van-icon name="cluster-o" />
                  </span>
                  <span class="channel-title">群机器人 Webhook</span>
                </div>
                <span class="st-status-tag st-status-tag--neutral">企微/钉钉/飞书</span>
              </div>
              <van-field
                v-model="notifConfig.webhook_url"
                label="Webhook"
                label-width="70px"
                center
                class="channel-field"
                placeholder="群机器人的完整 Webhook 链接"
              >
                <template #button>
                  <van-button
                    size="small"
                    type="default"
                    class="channel-test-btn"
                    :loading="testingChannel === 'webhook'"
                    @click="handleTestChannel('webhook', notifConfig.webhook_url)"
                  >
                    测试
                  </van-button>
                </template>
              </van-field>
            </div>

            <!-- 保存配置按钮 -->
            <div style="margin-top: 14px;">
              <van-button
                type="primary"
                block
                round
                class="notif-save-btn"
                :loading="savingConfig"
                @click="handleSaveConfig"
              >
                保存推送设置
              </van-button>
            </div>
          </div>
        </div>

        <!-- 卡片 2: 学科与满分管理 (可折叠) -->
        <div class="st-card st-collapse-card" :class="{ 'is-open': isSectionOpen('subject') }">
          <div class="st-collapse-header" @click="toggleSection('subject')">
            <div class="st-collapse-header-left">
              <span class="st-icon-badge st-icon-badge--purple">
                <van-icon name="apps-o" />
              </span>
              <div class="st-collapse-title-group">
                <span class="st-collapse-title">学科与满分管理</span>
                <span class="st-collapse-summary">{{ subjectSummaryText }}</span>
              </div>
            </div>
            <div class="st-collapse-header-right">
              <van-icon name="arrow-down" class="st-collapse-arrow" />
            </div>
          </div>

          <div class="st-collapse-body" v-show="isSectionOpen('subject')">
            <div class="card-hint-text">
              点击学科可调整满分分值（如100/120/150分），支持添加或删除自定义学科。
            </div>

            <div class="subject-cell-list">
              <van-cell
                v-for="sub in subjects"
                :key="sub.id"
                :title="sub.name"
                :label="sub.is_default ? '预置核心学科' : '自定义拓展学科'"
                is-link
                @click="openEditSubject(sub)"
              >
                <template #right-icon>
                  <div class="subject-cell-right">
                    <span class="subject-score-val">{{ sub.full_score }} 分</span>
                    <van-icon name="edit" class="subject-edit-icon" />
                  </div>
                </template>
              </van-cell>
            </div>

            <van-cell
              title="新增自定义学科"
              icon="plus"
              is-link
              class="add-subject-cell"
              @click="openAddSubject"
            />
          </div>
        </div>

        <!-- 卡片 3: 月度打卡深度分析图表 (可折叠) -->
        <div class="st-card st-collapse-card" :class="{ 'is-open': isSectionOpen('chart') }">
          <div class="st-collapse-header" @click="toggleSection('chart')">
            <div class="st-collapse-header-left">
              <span class="st-icon-badge st-icon-badge--info">
                <van-icon name="bar-chart-o" />
              </span>
              <div class="st-collapse-title-group">
                <span class="st-collapse-title">出勤深度图表分析</span>
                <span class="st-collapse-summary">{{ chartSummaryText }}</span>
              </div>
            </div>
            <div class="st-collapse-header-right">
              <van-icon name="arrow-down" class="st-collapse-arrow" />
            </div>
          </div>

          <div class="st-collapse-body" v-show="isSectionOpen('chart')">
            <div class="monthly-analytics-box">
              <!-- 整月每日作业量与打卡率走势混合图 -->
              <div class="monthly-chart-title">
                <van-icon name="chart-trending-o" color="#2563eb" style="margin-right: 4px;" />
                每日作业量与打卡率走势 (1~{{ monthlyData?.total_days || 30 }}日)
              </div>
              <div ref="monthlyTrendChartRef" class="monthly-echarts-container"></div>

              <!-- 各科目未完成频次分布柱状图 -->
              <div class="monthly-chart-title" style="margin-top: 14px;">
                <van-icon name="bar-chart-o" color="#f59e0b" style="margin-right: 4px;" />
                各科目未完成频次分布
              </div>
              <div v-show="monthlyData?.subject_missing_distribution?.length > 0" ref="monthlyMissingChartRef" class="monthly-echarts-container bar-height"></div>
              <div v-if="!monthlyData?.subject_missing_distribution?.length" class="monthly-perfect-tip">
                <van-icon name="passed" color="#10b981" style="margin-right: 4px;" />
                本月暂无科目未完成记录，各项作业皆如期完成！
              </div>
            </div>
          </div>
        </div>

        <!-- 卡片 4: OCR 识别引擎设置 (可折叠) -->
        <div class="st-card st-collapse-card" :class="{ 'is-open': isSectionOpen('ocr') }">
          <div class="st-collapse-header" @click="toggleSection('ocr')">
            <div class="st-collapse-header-left">
              <span class="st-icon-badge st-icon-badge--purple">
                <van-icon name="photograph" />
              </span>
              <div class="st-collapse-title-group">
                <span class="st-collapse-title">OCR 识别引擎设置</span>
                <span class="st-collapse-summary">{{ ocrSummaryText }}</span>
              </div>
            </div>
            <div class="st-collapse-header-right">
              <van-icon name="arrow-down" class="st-collapse-arrow" />
            </div>
          </div>

          <div class="st-collapse-body" v-show="isSectionOpen('ocr')">
            <van-cell
              title="当前生效推理引擎"
              :value="ocrConfig.active_engine === 'CloudVLM' ? '智谱 GLM-4V-Flash（高精度云端）' : 'RapidOCR（本地轻量 CPU）'"
              :label="ocrConfig.has_cloud_key ? '已开启云端多模态视觉模型，复杂排版与手写体优先使用' : '当前使用本地 CPU 模型；配置免费智谱 Key 可大幅提升作业与错题手写识别率'"
            />

            <van-cell-group inset style="margin: 8px 0;">
              <van-field
                v-model="ocrKeyInput"
                type="password"
                label="云端 API Key"
                :placeholder="ocrConfig.has_cloud_key ? '已配置: ' + ocrConfig.cloud_key_masked : '智谱开放平台免费 Key (留空使用本地离线)'"
                clearable
              />
            </van-cell-group>

            <div class="ocr-card-actions">
              <van-button
                type="primary"
                size="small"
                round
                :loading="savingOcr"
                @click="saveOcrSettings"
              >
                保存 OCR 设置
              </van-button>
              <van-button
                v-if="ocrConfig.has_cloud_key"
                plain
                type="danger"
                size="small"
                round
                @click="clearOcrKey"
              >
                恢复纯本地离线
              </van-button>
            </div>
            <div class="card-hint-text" style="margin-top: 8px;">
              说明：智谱 GLM-4V-Flash 视觉模型永久免费。前往 bigmodel.cn 注册即可免费获取 API Key。若不配置则默认使用本地 CPU RapidOCR 离线引擎。
            </div>
          </div>
        </div>

        <!-- 卡片 5: 数据安全与全站备份 (可折叠) -->
        <div class="st-card st-collapse-card" :class="{ 'is-open': isSectionOpen('backup') }">
          <div class="st-collapse-header" @click="toggleSection('backup')">
            <div class="st-collapse-header-left">
              <span class="st-icon-badge st-icon-badge--success">
                <van-icon name="shield-o" />
              </span>
              <div class="st-collapse-title-group">
                <span class="st-collapse-title">数据安全与备份</span>
                <span class="st-collapse-summary">{{ backupSummaryText }}</span>
              </div>
            </div>
            <div class="st-collapse-header-right">
              <van-icon name="arrow-down" class="st-collapse-arrow" />
            </div>
          </div>

          <div class="st-collapse-body" v-show="isSectionOpen('backup')">
            <van-cell title="全站数据导出备份" is-link label="包含 SQLite 数据库与所有错题高清原图" @click="handleExportBackup" />
            <van-cell title="从备份 Zip 包还原" label="恢复前将自动在本地创建数据快照">
              <template #right-icon>
                <van-uploader :after-read="handleImportBackup" accept=".zip">
                  <van-button size="small" type="primary">选择并还原</van-button>
                </van-uploader>
              </template>
            </van-cell>
          </div>
        </div>

        <!-- 卡片 6: 安全设置与系统关于 (可折叠) -->
        <div class="st-card st-collapse-card" :class="{ 'is-open': isSectionOpen('security') }">
          <div class="st-collapse-header" @click="toggleSection('security')">
            <div class="st-collapse-header-left">
              <span class="st-icon-badge st-icon-badge--neutral">
                <van-icon name="setting-o" />
              </span>
              <div class="st-collapse-title-group">
                <span class="st-collapse-title">安全口令与关于</span>
                <span class="st-collapse-summary">{{ securitySummaryText }}</span>
              </div>
            </div>
            <div class="st-collapse-header-right">
              <van-icon name="arrow-down" class="st-collapse-arrow" />
            </div>
          </div>

          <div class="st-collapse-body" v-show="isSectionOpen('security')">
            <van-cell title="修改管理口令" is-link icon="lock" @click="showChangePin = true" />
            <van-cell title="系统关于与运行自检" is-link icon="info-o" @click="$router.push('/about')" />
            <van-cell title="退出管理并锁定口令" is-link icon="cross" @click="lockSettings" />
          </div>
        </div>
      </div>
    </div>

    <!-- 编辑学科分值与名称弹窗 -->
    <van-dialog
      v-model:show="showEditSubject"
      title="编辑学科"
      show-cancel-button
      confirm-button-text="保存分值"
      @confirm="submitEditSubject"
    >
      <div style="padding: 1.25rem 1rem 0.5rem;">
        <van-field
          v-model="editSubForm.name"
          label="学科名称"
          :readonly="editSubForm.is_default"
          :placeholder="editSubForm.is_default ? '预置核心学科名称不可修改' : '请输入学科名称'"
        />
        <van-field
          v-model="editSubForm.full_score"
          type="number"
          label="满分分值"
          placeholder="如 100 / 120 / 150"
        />
        <div v-if="editSubForm.is_default" class="edit-dialog-tip">
          注：系统预置核心学科名称受保护不可删除，仅支持根据当地中考标准修改满分分值。
        </div>
        <div v-else style="margin-top: 14px; text-align: center;">
          <van-button
            type="danger"
            plain
            size="small"
            block
            round
            icon="delete-o"
            @click="handleDeleteSubject"
          >
            删除此自定义学科
          </van-button>
        </div>
      </div>
    </van-dialog>

    <!-- 新增学科弹窗 -->
    <van-dialog
      v-model:show="showAddSubject"
      title="新增学科"
      show-cancel-button
      confirm-button-text="添加"
      @confirm="submitAddSubject"
    >
      <div style="padding: 1.25rem 1rem 0.5rem;">
        <van-field v-model="newSub.name" label="学科名称" placeholder="如：科学 / 物理 / 法语" />
        <van-field v-model="newSub.full_score" type="number" label="满分分值" placeholder="100" />
      </div>
    </van-dialog>

    <!-- 修改口令弹窗 -->
    <van-dialog
      v-model:show="showChangePin"
      title="修改管理口令"
      show-cancel-button
      confirm-button-text="确认修改"
      @confirm="submitChangePin"
    >
      <div style="padding: 1.25rem 1rem 0.5rem;">
        <van-field v-model="pinForm.oldPin" type="password" label="原口令" placeholder="请输入原口令" />
        <van-field v-model="pinForm.newPin" type="password" label="新口令" placeholder="请输入新口令 (至少4位)" />
      </div>
    </van-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue';
import { showToast, showConfirmDialog, showDialog } from 'vant';
import { settingsApi, backupApi, notificationApi, examApi } from '../api';
import echarts from '../utils/echarts';

const isUnlocked = ref(sessionStorage.getItem('parent_unlocked') === 'true');
const inputPin = ref('');
const verifying = ref(false);
const subjects = ref([]);

// 折叠卡片状态管理 (默认全部收起，一屏尽收眼底)
const activeSections = ref([]);
const allSectionKeys = ['notif', 'subject', 'chart', 'ocr', 'backup', 'security'];

const isSectionOpen = (key) => activeSections.value.includes(key);

const toggleSection = (key) => {
  const idx = activeSections.value.indexOf(key);
  if (idx > -1) {
    activeSections.value.splice(idx, 1);
  } else {
    activeSections.value.push(key);
    if (key === 'chart') {
      nextTick(() => {
        handleSettingsResize();
        renderMonthlyCharts();
      });
    }
  }
};

const areAllExpanded = computed(() => activeSections.value.length === allSectionKeys.length);

const toggleAllSections = () => {
  if (areAllExpanded.value) {
    activeSections.value = [];
  } else {
    activeSections.value = [...allSectionKeys];
    nextTick(() => {
      handleSettingsResize();
      renderMonthlyCharts();
    });
  }
};

// 状态摘要文本计算
const notifSummaryText = computed(() => {
  const channels = notifConfig.value.enabled_channels || [];
  if (!channels.length) return '未启用任何渠道';
  const labels = [];
  if (channels.includes('wechat_sandbox')) {
    labels.push(`微信(${wechatMemberList.value.length}人)`);
  }
  if (channels.includes('serverchan')) labels.push('Server酱');
  if (channels.includes('bark')) labels.push('Bark');
  if (channels.includes('webhook')) labels.push('群机器人');
  return `已启用 ${channels.length} 个渠道（${labels.join(' · ')}）`;
});

const subjectSummaryText = computed(() => {
  const count = subjects.value.length;
  if (!count) return '暂未配置学科';
  const preview = subjects.value.slice(0, 3).map(s => s.name).join('/');
  return `已配置 ${count} 门学科（${preview}等）`;
});

const chartSummaryText = computed(() => {
  return `${currentYear.value}年${currentMonth.value}月 · 走势图与缺卡分布`;
});

const ocrSummaryText = computed(() => {
  if (ocrConfig.value.active_engine === 'CloudVLM') {
    return '智谱大模型 GLM-4V-Flash（高精度云端）';
  }
  return 'RapidOCR（本地轻量 CPU 离线）';
});

const backupSummaryText = computed(() => {
  return '全站 SQLite 数据库与错题原图备份 / 还原';
});

const securitySummaryText = computed(() => {
  return '管理口令 · 系统关于与自检 · 安全退出';
});

// 学科编辑与新增
const showEditSubject = ref(false);
const editSubForm = ref({ id: null, name: '', full_score: 100, is_default: true });
const showAddSubject = ref(false);
const newSub = ref({ name: '', full_score: 100 });

// 口令修改
const showChangePin = ref(false);
const pinForm = ref({ oldPin: '', newPin: '' });

// OCR 模型与配置
const ocrConfig = ref({
  active_engine: 'RapidOCR',
  has_cloud_key: false,
  cloud_key_masked: '',
  cloud_base_url: '',
  cloud_model: ''
});
const ocrKeyInput = ref('');
const savingOcr = ref(false);

// 通知配置状态
const notifConfig = ref({
  enabled_channels: ['wechat_sandbox'],
  wechat_app_id: 'wx631c06dc9c8a1819',
  wechat_app_secret: '088fa6a0c2d1bc5fdefd152bba06d66d',
  wechat_template_id: '6LSmd6HG59OXRqCoHbzG5pVHPDpi7KcgsHQuFcU3t_E',
  wechat_open_ids: '',
  wxpusher_app_token: 'AT_1FbRplPKgMYqeZtM8GEN4kkCE3LMGYqQ',
  wxpusher_topic_id: '46425',
  pushplus_token: '',
  serverchan_key: '',
  bark_key: '',
  webhook_url: '',
  reminder_slots: ['20:10', '21:10', '21:50']
});

// 结构化家庭成员 OpenID 列表
const wechatMemberList = ref([
  { name: '爸爸', openid: 'oz1nN3D7D2MKPBE0ah2CmroanhVc' },
  { name: '妈妈', openid: 'oz1nN3CuVUQ4S8yJ4PWU6wY2jsmo' }
]);

const parseWechatMembersFromConfig = (raw) => {
  if (!raw || !String(raw).trim()) {
    return [{ name: '爸爸', openid: '' }];
  }
  const rawStr = String(raw).trim();
  if (rawStr.startsWith('[') && rawStr.endsWith(']')) {
    try {
      const arr = JSON.parse(rawStr);
      if (Array.isArray(arr) && arr.length > 0) {
        return arr.map((item, idx) => ({
          name: item.name || `成员${idx + 1}`,
          openid: item.openid || ''
        }));
      }
    } catch (e) {}
  }
  const tokens = rawStr.split(/[,;\n]+/).map(s => s.trim()).filter(Boolean);
  if (tokens.length === 0) return [{ name: '爸爸', openid: '' }];
  return tokens.map((tok, idx) => {
    if (tok.includes(':') || tok.includes('：')) {
      const parts = tok.split(/[:：]/);
      return { name: parts[0].trim() || `成员${idx + 1}`, openid: parts[1]?.trim() || '' };
    }
    const defaultName = idx === 0 ? '爸爸' : (idx === 1 ? '妈妈' : `成员${idx + 1}`);
    return { name: defaultName, openid: tok };
  });
};

const serializeWechatMembers = () => {
  const valid = wechatMemberList.value.filter(m => m.openid && m.openid.trim());
  return JSON.stringify(valid);
};

const addWechatMember = () => {
  const count = wechatMemberList.value.length;
  const nextName = count === 0 ? '爸爸' : (count === 1 ? '妈妈' : `家庭成员${count + 1}`);
  wechatMemberList.value.push({ name: nextName, openid: '' });
};

const removeWechatMember = (idx) => {
  wechatMemberList.value.splice(idx, 1);
  notifConfig.value.wechat_open_ids = serializeWechatMembers();
};

const testSingleMember = async (m, idx) => {
  if (!m.openid || !m.openid.trim()) {
    showToast(`请先输入【${m.name || '成员'}】的微信 OpenID`);
    return;
  }
  testingChannel.value = `wechat_single_${idx}`;
  try {
    const singlePayload = JSON.stringify([{ name: m.name || '家人', openid: m.openid.trim() }]);
    const res = await notificationApi.testChannel('wechat_sandbox', {
      target: singlePayload,
      app_id: notifConfig.value.wechat_app_id,
      app_secret: notifConfig.value.wechat_app_secret,
      template_id: notifConfig.value.wechat_template_id
    });
    if (res.data.success) {
      showDialog({
        title: '测试发送成功',
        message: `已向【${m.name}】的微信发送测试卡片，请查看手机微信！`,
        confirmButtonText: '好'
      });
    } else {
      showDialog({
        title: '测试未成功',
        message: res.data.message || '请检查 OpenID 是否正确',
        confirmButtonText: '知道了'
      });
    }
  } catch (e) {
    showToast(e.response?.data?.detail || e.message || '测试失败');
  } finally {
    testingChannel.value = '';
  }
};
const savingConfig = ref(false);
const testingChannel = ref('');
const sendingSummary = ref(false);

const toggleChannel = (key) => {
  const list = notifConfig.value.enabled_channels;
  const idx = list.indexOf(key);
  if (idx > -1) {
    list.splice(idx, 1);
  } else {
    list.push(key);
  }
};

// 月度深度看板状态与图表
const currentYear = ref(new Date().getFullYear());
const currentMonth = ref(new Date().getMonth() + 1);
const monthlyData = ref(null);
const monthlyTrendChartRef = ref(null);
const monthlyMissingChartRef = ref(null);
let monthlyTrendChartInstance = null;
let monthlyMissingChartInstance = null;

const handleVerifyPin = async () => {
  if (!inputPin.value) {
    showToast('请输入口令');
    return;
  }
  verifying.value = true;
  try {
    const res = await settingsApi.verifyPin(inputPin.value);
    isUnlocked.value = true;
    sessionStorage.setItem('parent_unlocked', 'true');
    sessionStorage.setItem('parent_pin', inputPin.value);
    showToast({ message: '解锁成功', icon: 'success' });
    fetchSubjects();
    fetchNotificationConfig();
    fetchMonthlyAnalytics();
    fetchOcrConfig();

    if (res.data?.is_default_pin) {
      showDialog({
        title: '⚠️ 安全加固提醒',
        message: '系统当前正在使用初始默认口令 (888888)。为了防止公网未授权访问与数据泄露，强烈建议立即修改管理口令！',
        confirmButtonText: '立即修改',
        confirmButtonColor: '#e11d48',
        showCancelButton: true,
        cancelButtonText: '稍后再说'
      }).then(() => {
        pinForm.value.oldPin = inputPin.value;
        pinForm.value.newPin = '';
        showChangePin.value = true;
      }).catch(() => {});
    }
  } catch (e) {
    const msg = e.response?.data?.detail || '口令错误';
    showToast({ message: msg, icon: 'cross' });
  } finally {
    verifying.value = false;
  }
};

const lockSettings = () => {
  isUnlocked.value = false;
  sessionStorage.removeItem('parent_unlocked');
  sessionStorage.removeItem('parent_pin');
  inputPin.value = '';
  showToast('已安全退出家长模式');
};

const fetchOcrConfig = async () => {
  try {
    const res = await settingsApi.getOcrConfig();
    ocrConfig.value = res.data;
  } catch (e) {
    console.error('获取OCR配置失败', e);
  }
};

const saveOcrSettings = async () => {
  if (!ocrKeyInput.value.trim()) {
    showToast('请输入 API Key 或点击恢复纯本地离线');
    return;
  }
  savingOcr.value = true;
  try {
    await settingsApi.updateOcrConfig({
      api_key: ocrKeyInput.value.trim()
    });
    showToast({ message: 'OCR 设置已更新', icon: 'success' });
    ocrKeyInput.value = '';
    await fetchOcrConfig();
  } catch (e) {
    showToast('保存失败');
  } finally {
    savingOcr.value = false;
  }
};

const clearOcrKey = async () => {
  try {
    await settingsApi.updateOcrConfig({ api_key: '' });
    showToast('已切换为纯本地离线模式');
    ocrKeyInput.value = '';
    await fetchOcrConfig();
  } catch (e) {
    showToast('重置失败');
  }
};

const fetchSubjects = async () => {
  try {
    const res = await settingsApi.getSubjects();
    subjects.value = res.data;
  } catch (e) {
    console.error('获取学科列表失败', e);
  }
};

const openEditSubject = (sub) => {
  editSubForm.value = {
    id: sub.id,
    name: sub.name,
    full_score: sub.full_score,
    is_default: !!sub.is_default
  };
  showEditSubject.value = true;
};

const submitEditSubject = async () => {
  if (!editSubForm.value.id) return;
  const score = parseFloat(editSubForm.value.full_score);
  if (isNaN(score) || score <= 0) {
    showToast('请输入有效的满分分值');
    return;
  }
  try {
    await settingsApi.updateSubject(editSubForm.value.id, {
      name: editSubForm.value.name.trim(),
      full_score: score
    });
    showToast({ message: '学科满分已更新', icon: 'success' });
    showEditSubject.value = false;
    fetchSubjects();
  } catch (e) {
    showToast(e.response?.data?.detail || '修改失败');
  }
};

const handleDeleteSubject = () => {
  if (editSubForm.value.is_default) {
    showToast('系统预置核心学科不可删除');
    return;
  }
  showConfirmDialog({
    title: '确认删除学科',
    message: `确定要删除学科“${editSubForm.value.name}”吗？关联的历史记录将予以保留。`
  }).then(async () => {
    try {
      await settingsApi.deleteSubject(editSubForm.value.id);
      showToast({ message: '学科已删除', icon: 'success' });
      showEditSubject.value = false;
      fetchSubjects();
    } catch (e) {
      showToast(e.response?.data?.detail || '删除失败');
    }
  }).catch(() => {});
};

const openAddSubject = () => {
  newSub.value = { name: '', full_score: 100 };
  showAddSubject.value = true;
};

const submitAddSubject = async () => {
  if (!newSub.value.name.trim()) {
    showToast('请填写学科名称');
    return;
  }
  const score = parseFloat(newSub.value.full_score);
  if (isNaN(score) || score <= 0) {
    showToast('请输入有效的满分分值');
    return;
  }
  try {
    await settingsApi.createSubject({
      name: newSub.value.name.trim(),
      full_score: score,
      sort_order: subjects.value.length + 1
    });
    showToast({ message: '学科已添加', icon: 'success' });
    showAddSubject.value = false;
    newSub.value = '';
    fetchSubjects();
  } catch (e) {
    showToast(e.response?.data?.detail || '添加失败');
  }
};

const fetchNotificationConfig = async () => {
  try {
    const res = await notificationApi.getConfig();
    notifConfig.value = res.data;
    if (res.data.wechat_open_ids) {
      wechatMemberList.value = parseWechatMembersFromConfig(res.data.wechat_open_ids);
    }
  } catch (e) {
    console.error('Failed to load notification config:', e);
  }
};

const handleSaveConfig = async () => {
  savingConfig.value = true;
  try {
    notifConfig.value.wechat_open_ids = serializeWechatMembers();
    await notificationApi.updateConfig(notifConfig.value);
    showToast({ message: '通知设置已保存', icon: 'success' });
  } catch (e) {
    showToast('保存失败');
  } finally {
    savingConfig.value = false;
  }
};

const handleTestChannel = async (channel, payload) => {
  const targetVal = typeof payload === 'string' ? payload : (payload?.target || '');
  if (!targetVal || !targetVal.trim()) {
    showToast('请先输入要测试的配置或接收人 OpenID/Key');
    return;
  }
  testingChannel.value = channel;
  try {
    const res = await notificationApi.testChannel(channel, payload);
    if (res.data.success) {
      showDialog({
        title: '测试发送成功',
        message: res.data.message || '请查看手机个人微信收到的推送卡片！',
        confirmButtonText: '好'
      });
    } else {
      showDialog({
        title: '测试发送未成功',
        message: res.data.message || '请检查配置或网络',
        confirmButtonText: '知道了'
      });
    }
  } catch (e) {
    const msg = e.response?.data?.detail || e.message || '测试请求失败';
    showDialog({
      title: '测试接口异常',
      message: msg,
      confirmButtonText: '知道了'
    });
  } finally {
    testingChannel.value = '';
  }
};

const handleSendSummaryNow = async () => {
  showConfirmDialog({
    title: '确认发送今日汇总',
    message: '系统将立即聚合今日所有作业状态、连续打卡天数与艾宾浩斯复习情况，向所有已启用渠道推送一份最新日报快照。确定发送吗？'
  }).then(async () => {
    sendingSummary.value = true;
    try {
      const res = await notificationApi.sendSummaryNow();
      if (res.data.success) {
        showDialog({
          title: '发送成功',
          message: '今日作业与复习快报已成功送达！',
          confirmButtonText: '确定'
        });
      } else {
        const msg = res.data.message || '部分渠道发送失败，请在上方检查各通道配置。';
        const isRateLimited = msg.includes('秒') || msg.includes('等待') || msg.includes('频繁');
        showDialog({
          title: isRateLimited ? '操作提示' : '发送未完成',
          message: msg,
          confirmButtonText: '知道了'
        });
      }
    } catch (e) {
      const errMsg = e.response?.data?.detail || e.response?.data?.message || '发送接口失败';
      showToast(errMsg);
    } finally {
      sendingSummary.value = false;
    }
  });
};

const handleExportBackup = () => {
  showConfirmDialog({
    title: '导出安全提示',
    message: '导出的 Zip 压缩包包含本地数据库与通知密钥等敏感凭据，请妥善保存在私密设备中，切勿公开外传。确认立即导出备份？',
    confirmButtonText: '确认导出',
    cancelButtonText: '取消',
    confirmButtonColor: '#2563eb'
  }).then(async () => {
    showToast({ message: '正在生成备份压缩包...', duration: 2000 });
    try {
      const res = await backupApi.exportBackup();
      const blob = new Blob([res.data], { type: 'application/zip' });
      const downloadUrl = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = downloadUrl;
      const now = new Date();
      const timeStr = `${now.getFullYear()}${String(now.getMonth()+1).padStart(2, '0')}${String(now.getDate()).padStart(2, '0')}_${String(now.getHours()).padStart(2, '0')}${String(now.getMinutes()).padStart(2, '0')}`;
      link.setAttribute('download', `study_trace_backup_${timeStr}.zip`);
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(downloadUrl);
      showToast({ message: '已完成备份下载', icon: 'passed' });
    } catch (e) {
      showToast(e.response?.data?.detail || '导出失败，请检查口令权限');
    }
  }).catch(() => {});
};

const handleImportBackup = async (fileItem) => {
  showConfirmDialog({
    title: '确认数据还原',
    message: '还原将自动在本地先创建一份快照。确定要执行备份恢复吗？'
  }).then(async () => {
    showToast({ message: '正在解析还原备份...', duration: 2000 });
    try {
      const formData = new FormData();
      formData.append('file', fileItem.file);
      const res = await backupApi.importBackup(formData);
      showToast({ message: `还原成功！已自动创建快照: ${res.data.pre_restore_snapshot}`, icon: 'success' });
      fetchSubjects();
      fetchNotificationConfig();
    } catch (e) {
      showToast('还原失败，请检查备份文件');
    }
  });
};

const submitChangePin = async () => {
  if (!pinForm.value.oldPin || !pinForm.value.newPin) {
    showToast('请完整输入口令');
    return;
  }
  try {
    await settingsApi.changePin(pinForm.value.oldPin, pinForm.value.newPin);
    sessionStorage.setItem('parent_pin', pinForm.value.newPin);
    showToast({ message: '口令修改成功', icon: 'success' });
    pinForm.value = { oldPin: '', newPin: '' };
  } catch (e) {
    showToast(e.response?.data?.detail || '修改失败');
  }
};

const changeMonth = (delta) => {
  let y = currentYear.value;
  let m = currentMonth.value + delta;
  if (m > 12) {
    m = 1;
    y += 1;
  } else if (m < 1) {
    m = 12;
    y -= 1;
  }
  currentYear.value = y;
  currentMonth.value = m;
  fetchMonthlyAnalytics();
};

const fetchMonthlyAnalytics = async () => {
  try {
    const res = await examApi.getMonthlyAnalytics(currentYear.value, currentMonth.value);
    monthlyData.value = res.data;
    renderMonthlyCharts();
  } catch (e) {
    console.error('Failed to load monthly analytics:', e);
  }
};

const renderMonthlyCharts = () => {
  nextTick(() => {
    // 1. 每日作业量与打卡率走势双轴混合图 (柱状图+折线图)
    if (monthlyTrendChartRef.value) {
      if (!monthlyTrendChartInstance) {
        monthlyTrendChartInstance = echarts.init(monthlyTrendChartRef.value);
      }
      const days = monthlyData.value?.daily_trends?.map(d => `${parseInt(d.date.split('-')[2])}日`) || [];
      const rates = monthlyData.value?.daily_trends?.map(d => (d.total > 0 ? d.rate : null)) || [];
      const totals = monthlyData.value?.daily_trends?.map(d => (d.total > 0 ? d.total : 0)) || [];

      // 优雅计算 5 的整倍数作为 Y 轴上限，保证刻度均匀且美观 (如 5, 10, 15, 20)
      const maxTotal = totals.length > 0 ? Math.max(...totals, 4) : 4;
      const y1Max = Math.max(5, Math.ceil((maxTotal * 1.2) / 5) * 5);

      monthlyTrendChartInstance.setOption({
        tooltip: {
          trigger: 'axis',
          axisPointer: {
            type: 'shadow',
            shadowStyle: { color: 'rgba(241, 245, 249, 0.65)' }
          },
          backgroundColor: 'rgba(255, 255, 255, 0.96)',
          borderColor: '#e2e8f0',
          borderWidth: 1,
          padding: [8, 10],
          textStyle: { color: '#0f172a', fontSize: 11 },
          formatter: (params) => {
            const p = params[0];
            const item = monthlyData.value?.daily_trends?.[p.dataIndex];
            if (!item || item.total === 0) {
              return `<b>${item?.date || ''}</b><br/><span style="color: var(--st-text-muted);">当天无作业打卡安排</span>`;
            }
            return `
              <div style="font-size: var(--st-font-xs);font-weight:600;margin-bottom:4px;color:#0f172a;">${item.date}</div>
              <div style="display:flex;align-items:center;gap:6px;margin:2px 0;">
                <span style="display:inline-block;width:7px;height:7px;border-radius:2px;background:#3b82f6;"></span>
                <span>作业总量：<b>${item.total}</b> 项 (完成 ${item.completed} 项)</span>
              </div>
              <div style="display:flex;align-items:center;gap:6px;margin:2px 0;">
                <span style="display:inline-block;width:7px;height:7px;border-radius:50%;background:#10b981;"></span>
                <span>当天打卡率：<b style="color:#10b981;">${item.rate}%</b></span>
              </div>
            `;
          }
        },
        legend: {
          show: true,
          top: 0,
          right: 12,
          itemWidth: 10,
          itemHeight: 7,
          itemGap: 14,
          textStyle: { fontSize: 10, color: '#64748b' },
          data: ['作业总量', '打卡率']
        },
        grid: { top: 28, right: 38, bottom: 22, left: 28 },
        xAxis: {
          type: 'category',
          data: days,
          axisLabel: { fontSize: 10, color: '#64748b', interval: 4 },
          axisLine: { lineStyle: { color: '#e2e8f0' } },
          axisTick: { alignWithLabel: true }
        },
        yAxis: [
          {
            type: 'value',
            name: '项',
            nameTextStyle: { fontSize: 9, color: '#94a3b8', padding: [0, 0, 0, -8] },
            min: 0,
            max: y1Max,
            interval: y1Max / 4,
            axisLabel: { fontSize: 9, color: '#64748b' },
            splitLine: { lineStyle: { color: '#f1f5f9', type: 'dashed' } }
          },
          {
            type: 'value',
            min: 0,
            max: 100,
            interval: 25,
            axisLabel: { formatter: '{value}%', fontSize: 9, color: '#10b981' },
            splitLine: { show: false }
          }
        ],
        series: [
          {
            name: '作业总量',
            type: 'bar',
            yAxisIndex: 0,
            data: totals,
            barMaxWidth: 11,
            itemStyle: {
              color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                { offset: 0, color: '#60a5fa' },
                { offset: 1, color: '#c7d2fe' }
              ]),
              borderRadius: [3, 3, 0, 0]
            }
          },
          {
            name: '打卡率',
            type: 'line',
            yAxisIndex: 1,
            data: rates,
            smooth: 0.25,
            connectNulls: true,
            showSymbol: true,
            symbol: 'circle',
            symbolSize: 5,
            z: 3,
            itemStyle: {
              color: '#10b981',
              borderWidth: 1.5,
              borderColor: '#ffffff'
            },
            lineStyle: { width: 2.2, color: '#10b981' }
          }
        ]
      }, true);
    }

    // 2. 各科未完成频次分布柱状图
    if (monthlyMissingChartRef.value && monthlyData.value?.subject_missing_distribution?.length > 0) {
      if (!monthlyMissingChartInstance) {
        monthlyMissingChartInstance = echarts.init(monthlyMissingChartRef.value);
      }
      const subs = monthlyData.value.subject_missing_distribution.map(s => s.subject_name);
      const counts = monthlyData.value.subject_missing_distribution.map(s => s.missing_count);

      monthlyMissingChartInstance.setOption({
        tooltip: {
          trigger: 'axis',
          formatter: '{b}: 遗漏未完成 {c} 次'
        },
        grid: { top: 25, right: 15, bottom: 25, left: 35 },
        xAxis: {
          type: 'category',
          data: subs,
          axisLabel: { fontSize: 11, color: '#475569' },
          axisLine: { lineStyle: { color: '#e2e8f0' } }
        },
        yAxis: {
          type: 'value',
          minInterval: 1,
          axisLabel: { fontSize: 10, color: '#64748b' },
          splitLine: { lineStyle: { color: '#f1f5f9', type: 'dashed' } }
        },
        series: [
          {
            name: '未完成次数',
            type: 'bar',
            data: counts,
            barWidth: '40%',
            itemStyle: {
              color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                { offset: 0, color: '#f59e0b' },
                { offset: 1, color: '#fbbf24' }
              ]),
              borderRadius: [4, 4, 0, 0]
            },
            label: {
              show: true,
              position: 'top',
              fontSize: 11,
              color: '#d97706'
            }
          }
        ]
      }, true);
    }
  });
};

const handleSettingsResize = () => {
  if (monthlyTrendChartInstance) monthlyTrendChartInstance.resize();
  if (monthlyMissingChartInstance) monthlyMissingChartInstance.resize();
};

onMounted(() => {
  window.addEventListener('resize', handleSettingsResize);
  if (isUnlocked.value) {
    fetchSubjects();
    fetchNotificationConfig();
    fetchMonthlyAnalytics();
    fetchOcrConfig();
  }
});

onUnmounted(() => {
  window.removeEventListener('resize', handleSettingsResize);
  if (monthlyTrendChartInstance) monthlyTrendChartInstance.dispose();
  if (monthlyMissingChartInstance) monthlyMissingChartInstance.dispose();
});
</script>

<style scoped>
.ocr-card-actions {
  display: flex;
  gap: 10px;
  margin-top: 10px;
}

.settings-view {
  flex: 1;
  background-color: var(--st-bg-page, #f8fafc);
}

.settings-container {
  padding: 12px 14px 16px;
  max-width: 600px;
  margin: 0 auto;
}

.settings-top-notice {
  margin-bottom: 14px;
  border-radius: var(--st-radius-sm, 8px);
}

.pin-gate-card {
  margin: 2.5rem auto;
  max-width: 440px;
  background: var(--st-bg-card, #ffffff);
  border-radius: var(--st-radius-md, 14px);
  padding: 2.5rem 1.5rem;
  text-align: center;
  border: 1px solid var(--st-border, #f1f5f9);
  box-shadow: var(--st-shadow-card);
}

.gate-icon-circle {
  width: 60px;
  height: 60px;
  background: var(--st-warning-light, #fffbeb);
  border-radius: var(--st-radius-full, 9999px);
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 1.25rem;
}

.pin-gate-card h3 {
  margin: 0 0 0.5rem;
  font-size: var(--st-font-xl);
  font-weight: 700;
  color: var(--st-text-primary);
}

.gate-tip {
  font-size: var(--st-font-sm);
  color: var(--st-text-secondary);
  margin-bottom: 1.5rem;
}

.pin-field {
  background: var(--st-bg-page, #f8fafc);
  border-radius: var(--st-radius-sm, 8px);
  border: 1px solid var(--st-border, #e2e8f0);
  font-size: 1.2rem;
  letter-spacing: 4px;
}

.channel-config-box {
  background: #f8fafc;
  margin: 10px 0;
  padding: 12px;
  border-radius: var(--st-radius-sm, 8px);
  border: 1px solid var(--st-border, #e2e8f0);
}

.channel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
  gap: 8px;
}

.channel-header-left {
  display: flex;
  align-items: center;
  gap: 6px;
}

.channel-title {
  font-size: var(--st-font-sm);
  font-weight: 600;
  color: var(--st-text-primary);
  white-space: nowrap;
}

.channel-field {
  background: transparent;
  padding: 6px 0 2px;
}

.channel-field :deep(.van-field__label) {
  width: 70px;
  font-size: var(--st-font-sm);
  font-weight: 600;
  color: var(--st-text-primary);
  margin-right: 8px;
}

.channel-field :deep(.van-field__control) {
  font-size: var(--st-font-sm);
}

.channel-test-btn {
  height: 28px;
  min-width: 52px;
  padding: 0 10px;
  font-size: var(--st-font-xs);
  border-radius: var(--st-radius-sm, 6px);
  /* 弹性行内不许把按钮文字挤成竖排（「全员广播测试」逐字换行） */
  white-space: nowrap;
  flex-shrink: 0;
}

/* 微信家庭成员结构化管理列表样式 */
.wechat-members-section {
  margin: 10px 0 6px;
  background: var(--st-bg-surface, #ffffff);
  border: 1px solid var(--st-border-light, #e2e8f0);
  border-radius: var(--st-radius-md, 10px);
  padding: 10px 12px;
}

.wechat-members-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.wechat-members-title {
  font-size: var(--st-font-sm);
  font-weight: 600;
  color: var(--st-text-primary);
  display: flex;
  align-items: center;
  gap: 5px;
  /* 给右侧「全员广播测试」按钮让位：放不下时标题省略号，而不是按钮文字竖排 */
  min-width: 0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.wechat-member-card {
  background: var(--st-bg-elevated, #f8fafc);
  border: 1px solid var(--st-border-light, #edf2f7);
  border-radius: var(--st-radius-sm, 8px);
  padding: 8px 10px;
  margin-bottom: 8px;
  transition: all 0.2s ease;
}

.wechat-member-card:hover {
  border-color: var(--st-primary-light, #bfdbfe);
}

.wechat-member-row-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
}

.wechat-member-identity {
  display: flex;
  align-items: center;
  gap: 6px;
  flex: 1;
}

.member-index-badge {
  font-size: var(--st-font-xs);
  font-weight: 700;
  color: var(--st-primary, #2563eb);
  background: var(--st-primary-light, #eff6ff);
  padding: 2px 6px;
  border-radius: 4px;
}

.member-name-input {
  border: 1px solid transparent;
  background: transparent;
  font-size: var(--st-font-sm);
  font-weight: 600;
  color: var(--st-text-primary);
  padding: 2px 6px;
  border-radius: 4px;
  max-width: 130px;
  outline: none;
}

.member-name-input:focus {
  background: #ffffff;
  border-color: var(--st-primary, #2563eb);
}

.wechat-member-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.member-single-test-btn {
  height: 24px;
  padding: 0 8px;
  font-size: var(--st-font-xs);
  border-radius: 4px;
  /* 同上：卡片行内按钮文字禁止竖排换行 */
  white-space: nowrap;
  flex-shrink: 0;
}

.member-del-btn {
  font-size: var(--st-font-xl);
  color: #ef4444;
  cursor: pointer;
  padding: 2px;
}

.member-del-btn:hover {
  opacity: 0.8;
}

.wechat-member-openid-box {
  width: 100%;
}

.member-openid-input {
  width: 100%;
  border: 1px solid var(--st-border-light, #cbd5e1);
  background: #ffffff;
  font-family: monospace;
  font-size: var(--st-font-xs);
  color: var(--st-text-primary);
  padding: 6px 8px;
  border-radius: 6px;
  outline: none;
  box-sizing: border-box;
}

.member-openid-input:focus {
  border-color: var(--st-primary, #2563eb);
  box-shadow: 0 0 0 2px rgba(37, 99, 235, 0.1);
}

.wechat-add-member-wrapper {
  margin-top: 4px;
}

.wechat-add-btn {
  border-style: dashed;
  height: 32px;
  font-size: var(--st-font-xs);
  border-radius: var(--st-radius-sm, 6px);
}

.channel-caption {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: var(--st-font-xs);
  color: var(--st-text-muted);
  line-height: var(--st-leading-tight);
  margin-top: 4px;
  padding: 0 2px;
}

.caption-icon {
  font-size: var(--st-font-xs);
  color: var(--st-text-muted);
  flex-shrink: 0;
}

/* 渠道多选网格选择器 */
.channel-selector-section {
  padding: 10px 2px 8px;
}

.channel-selector-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.selector-title {
  font-size: var(--st-font-sm);
  font-weight: 600;
  color: var(--st-text-primary);
}

.selector-count {
  font-size: var(--st-font-xs);
  color: var(--st-primary, #2563eb);
  font-weight: 500;
}

.selector-count-empty {
  font-size: var(--st-font-xs);
  color: var(--st-text-muted);
}

.channel-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 8px;
}

.channel-select-card {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 9px 10px;
  background-color: #f8fafc;
  border: 1.5px solid #e2e8f0;
  border-radius: var(--st-radius-md, 10px);
  cursor: pointer;
  transition: all 0.2s ease;
  user-select: none;
}

.channel-select-card:active {
  transform: scale(0.98);
}

.channel-select-card.is-active {
  background-color: #eff6ff;
  border-color: var(--st-primary, #2563eb);
  box-shadow: 0 2px 8px rgba(37, 99, 235, 0.08);
}

.channel-badge {
  width: 24px;
  height: 24px;
  font-size: var(--st-font-sm);
  flex-shrink: 0;
}

.channel-card-text {
  font-size: var(--st-font-sm);
  font-weight: 600;
  color: var(--st-text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.channel-empty-tip {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 16px 12px;
  margin: 10px 0;
  background-color: #f8fafc;
  border: 1px dashed #cbd5e1;
  border-radius: var(--st-radius-md, 10px);
  color: var(--st-text-secondary);
  font-size: var(--st-font-xs);
}

/* 底部操作按钮：同行并排双按钮 */
.notif-action-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 14px 0 0;
}

.notif-btn {
  height: 40px;
  font-size: var(--st-font-sm);
  font-weight: 600;
  white-space: nowrap;
}

.notif-btn-secondary {
  flex: 1.05;
}

.notif-btn-primary {
  flex: 1;
}

/* 学科管理卡片样式 */
.card-hint-text {
  font-size: var(--st-font-xs);
  color: var(--st-text-secondary);
  line-height: var(--st-leading-normal);
  margin-bottom: 10px;
  padding: 0 4px;
}

.subject-cell-list {
  border-radius: var(--st-radius-sm, 8px);
  overflow: hidden;
  border: 1px solid var(--st-border, #e2e8f0);
  margin-bottom: 10px;
}

.subject-cell-right {
  display: flex;
  align-items: center;
  gap: 6px;
}

.subject-score-val {
  font-size: var(--st-font-sm);
  font-weight: 600;
  color: var(--st-primary, #2563eb);
}

.subject-edit-icon {
  font-size: var(--st-font-md);
  color: var(--st-text-muted);
}

.add-subject-cell {
  background: #f8fafc;
  border: 1px dashed var(--st-primary-light, #bfdbfe);
  border-radius: var(--st-radius-sm, 8px);
  color: var(--st-primary, #2563eb);
  font-weight: 600;
}

.edit-dialog-tip {
  font-size: var(--st-font-xs);
  color: var(--st-text-secondary);
  background: #f8fafc;
  border-radius: var(--st-radius-sm, 6px);
  padding: 8px 10px;
  margin-top: 10px;
  line-height: var(--st-leading-tight);
}

/* 月度透视样式 */
.monthly-analytics-box {
  padding: 10px 0 4px;
}

.monthly-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.monthly-title-box {
  display: flex;
  align-items: center;
  gap: 6px;
}

.monthly-title {
  font-size: var(--st-font-sm);
  font-weight: 600;
  color: var(--st-text-primary);
}

.month-stepper {
  display: flex;
  align-items: center;
  gap: 6px;
}

.current-month-text {
  font-size: var(--st-font-xs);
  font-weight: 600;
  color: var(--st-primary, #2563eb);
}

.monthly-stats-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
  margin-bottom: 14px;
}

.monthly-stat-item {
  background: #f8fafc;
  border: 1px solid var(--st-border, #e2e8f0);
  border-radius: var(--st-radius-sm, 8px);
  padding: 10px 4px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 64px;
}

.m-stat-val {
  font-size: var(--st-font-lg);
  font-weight: 700;
  color: var(--st-text-primary);
  height: 22px;
  line-height: 22px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.m-stat-label {
  font-size: var(--st-font-xs);
  color: var(--st-text-secondary);
  height: 16px;
  line-height: 16px;
  margin-top: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.text-primary {
  color: var(--st-primary, #2563eb) !important;
}

.text-succ {
  color: var(--st-success, #10b981) !important;
}

.monthly-chart-title {
  font-size: var(--st-font-xs);
  font-weight: 600;
  color: var(--st-text-secondary);
  margin-bottom: 4px;
}

.monthly-echarts-container {
  width: 100%;
  height: 205px;
}

.monthly-echarts-container.bar-height {
  height: 170px;
}

.monthly-perfect-tip {
  font-size: var(--st-font-xs);
  color: #166534;
  background: #f0fdf4;
  padding: 10px 12px;
  border-radius: var(--st-radius-sm, 8px);
  border: 1px solid #bbf7d0;
  text-align: center;
  margin-top: 6px;
}

/* 常驻出勤核心看板样式 */
.overview-dashboard-card {
  margin-bottom: 12px;
  background: var(--st-bg-card, #ffffff);
  border-radius: 14px;
  padding: 14px 16px 12px;
  border: 1px solid var(--st-border, #f1f5f9);
  box-shadow: 0 1px 3px rgba(15, 23, 42, 0.04);
}

.overview-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.overview-title-group {
  display: flex;
  align-items: center;
  gap: 8px;
}

.overview-title {
  font-size: var(--st-font-lg);
  font-weight: 700;
  color: var(--st-text-primary);
}

.overview-quick-actions {
  display: flex;
  justify-content: center;
  margin-top: 4px;
}

.quick-summary-btn {
  height: 32px;
  padding: 0 16px;
  font-size: var(--st-font-xs);
  font-weight: 500;
}

/* 分类控制工具栏 */
.section-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 4px 4px 10px;
}

.section-toolbar-left {
  display: flex;
  align-items: center;
  gap: 6px;
}

.section-toolbar-title {
  font-size: var(--st-font-sm);
  font-weight: 600;
  color: #475569;
}

.section-toolbar-count {
  font-size: var(--st-font-xs);
  color: var(--st-text-muted);
  background: #f1f5f9;
  padding: 1px 6px;
  border-radius: 10px;
}

.section-toggle-all-btn {
  background: none;
  border: none;
  font-size: var(--st-font-xs);
  color: #2563eb;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 4px 8px;
  border-radius: 6px;
  transition: background-color 0.2s;
}

.section-toggle-all-btn:hover {
  background-color: #eff6ff;
}

/* 现代化折叠卡片 */
.st-collapse-card {
  margin-bottom: 10px;
  background: var(--st-bg-card, #ffffff);
  border-radius: 14px;
  border: 1px solid var(--st-border, #f1f5f9);
  box-shadow: 0 1px 3px rgba(15, 23, 42, 0.04);
  overflow: hidden;
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
}

.st-collapse-card.is-open {
  border-color: #cbd5e1;
  box-shadow: 0 4px 12px rgba(15, 23, 42, 0.05);
}

.st-collapse-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 14px;
  cursor: pointer;
  user-select: none;
  background: #ffffff;
  transition: background-color 0.15s ease;
}

.st-collapse-header:hover {
  background-color: #f8fafc;
}

.st-collapse-header:active {
  background-color: #f1f5f9;
}

.st-collapse-header-left {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
  flex: 1;
}

.st-collapse-title-group {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.st-collapse-title {
  font-size: var(--st-font-md);
  font-weight: 600;
  color: var(--st-text-primary);
  line-height: var(--st-leading-tight);
}

.st-collapse-summary {
  font-size: var(--st-font-xs);
  color: var(--st-text-secondary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 240px;
}

.st-collapse-header-right {
  display: flex;
  align-items: center;
  padding-left: 8px;
  flex-shrink: 0;
}

.st-collapse-arrow {
  font-size: var(--st-font-md);
  color: var(--st-text-muted);
  transition: transform 0.25s cubic-bezier(0.4, 0, 0.2, 1), color 0.2s ease;
}

.st-collapse-card.is-open .st-collapse-arrow {
  transform: rotate(180deg);
  color: #2563eb;
}

.st-collapse-body {
  padding: 4px 14px 14px;
  border-top: 1px solid #f1f5f9;
  animation: fadeIn 0.2s ease-in-out;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(-4px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.notif-save-btn {
  height: 38px;
  font-size: var(--st-font-md);
  font-weight: 600;
}
</style>
