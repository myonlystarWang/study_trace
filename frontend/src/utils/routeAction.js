/**
 * 动作型 URL（`?action=add` / `?action=focus`）用一次就作废。
 *
 * 各页 onMounted 会读 `route.query.action` 打开录入抽屉；若不清掉，
 * 这个参数会一直挂在地址栏上，用户随手刷新页面就会再弹一次录入窗。
 * 消费动作后调用本函数：只摘掉 action，保留 tab 等其余参数。
 */
export function consumeActionQuery(router, route) {
  const query = route?.query;
  if (!query || !Object.prototype.hasOwnProperty.call(query, 'action')) return;
  const { action, ...rest } = query;
  router.replace({ path: route.path, query: rest });
}
