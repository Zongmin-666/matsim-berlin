# find_affected_routes.py
from lxml import etree
import os

# --- 配置 ---
SCHEDULE_FILE = 'transitSchedule.xml.xml'
MARATHON_LINK_IDS_FILE = 'marathon_link_ids.txt'
OUTPUT_AFFECTED_ROUTES_FILE = 'affected_routes.txt'

print("--- 自动化第一步：开始批量识别受影响的公交路径 ---")

# 1. 读取并加载马拉松封锁路段ID
with open(MARATHON_LINK_IDS_FILE, 'r') as f:
    marathon_links = set(line.strip() for line in f)
print(f"加载了 {len(marathon_links)} 个封锁路段ID。")

# 2. 解析公交时刻表文件
if not os.path.exists(SCHEDULE_FILE):
    print(f"错误: 公交时刻表文件 '{SCHEDULE_FILE}' 不存在！")
    exit()

tree = etree.parse(SCHEDULE_FILE)
root = tree.getroot()

affected_routes_info = []

# 3. 遍历每一条公交线路和路径
print("正在扫描所有公交路径...")
for transit_line in root.iter('transitLine'):
    line_id = transit_line.get('id')
    for transit_route in transit_line.iter('transitRoute'):
        route_id = transit_route.get('id')

        route_links_element = transit_route.find('route')
        if route_links_element is None:
            continue

        # 提取路径中的所有路段ID
        route_links = {link.get('refId') for link in route_links_element.iter('link')}

        # 核心：检查路径路段和封锁路段是否有交集
        if not route_links.isdisjoint(marathon_links):
            # isdisjoint()是检查两个集合是否没有共同元素，not isdisjoint()就是有交集
            affected_routes_info.append(f"{line_id},{route_id}")  # 保存线路ID和路径ID

print(f"扫描完成！共找到 {len(affected_routes_info)} 条受影响的公交路径。")

# 4. 保存结果
with open(OUTPUT_AFFECTED_ROUTES_FILE, 'w') as f:
    for info in affected_routes_info:
        f.write(f"{info}\n")

print(f"已将受影响的路径信息保存到 '{OUTPUT_AFFECTED_ROUTES_FILE}'。")
print("--- 自动化第一步：完成！ ---")