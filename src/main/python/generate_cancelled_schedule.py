# generate_cancelled_schedule.py
from lxml import etree
import os

# --- 配置 ---
ORIGINAL_SCHEDULE_FILE = 'transitSchedule.xml.xml'
AFFECTED_ROUTES_FILE = 'affected_routes.txt' # 由 find_affected_routes.py 生成
MODIFIED_SCHEDULE_FILE = 'transitSchedule_cancelled_only.xml' # 新的输出文件名
REPORT_FILE = 'cancellation_report.txt' # 新的报告文件名

print("\n--- 脚本启动：模拟公交线路服务中断（取消）---")

# 1. 加载数据
print(f"正在读取受影响的线路列表: '{AFFECTED_ROUTES_FILE}'...")
if not os.path.exists(AFFECTED_ROUTES_FILE):
    print(f"错误: 找不到受影响线路文件 '{AFFECTED_ROUTES_FILE}'！请先运行 find_affected_routes.py。")
    exit()

with open(AFFECTED_ROUTES_FILE, 'r') as f:
    # 我们只需要 route_id 即可
    affected_route_ids = {line.strip().split(',')[1] for line in f}
print(f"共加载了 {len(affected_route_ids)} 条需要取消的公交路径。")


# 2. 解析原始公交时刻表
print(f"正在解析原始时刻表: '{ORIGINAL_SCHEDULE_FILE}'...")
parser = etree.XMLParser(remove_blank_text=True)
schedule_tree = etree.parse(ORIGINAL_SCHEDULE_FILE, parser)
schedule_root = schedule_tree.getroot()

# 3. 建立索引并执行删除操作
# 为了安全地删除，我们先找到所有要删除的元素
routes_to_delete = []
for transit_route in schedule_root.iter('transitRoute'):
    if transit_route.get('id') in affected_route_ids:
        routes_to_delete.append(transit_route)

print(f"正在从XML树中删除 {len(routes_to_delete)} 条路径...")
for route_element in routes_to_delete:
    parent = route_element.getparent()
    if parent is not None:
        parent.remove(route_element)

# 4. 保存修改后的新文件
print(f"正在保存修改后的文件: '{MODIFIED_SCHEDULE_FILE}'...")
schedule_tree.write(MODIFIED_SCHEDULE_FILE, pretty_print=True, xml_declaration=True, encoding='UTF-8')

# 5. 生成简单的报告
print(f"正在生成报告文件: '{REPORT_FILE}'...")
with open(REPORT_FILE, 'w', encoding='utf-8') as f:
    f.write(f"--- Transit Route Cancellation Report ---\n")
    f.write(f"Total routes cancelled: {len(routes_to_delete)}\n\n")
    f.write("--- List of Cancelled Route IDs ---\n")
    for route_id in sorted(list(affected_route_ids)):
        f.write(f"{route_id}\n")

print("\n--- 脚本执行完毕 ---")
print(f"成功取消了 {len(routes_to_delete)} 条公交路径。")
print(f"新的时刻表已保存至: '{MODIFIED_SCHEDULE_FILE}'")
print(f"详细报告已保存至: '{REPORT_FILE}'")