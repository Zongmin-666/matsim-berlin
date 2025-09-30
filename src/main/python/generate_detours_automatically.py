# generate_detours_automatically.py (V4 - 带详细报告输出)
from lxml import etree
import networkx as nx
import os

# --- 配置 ---
NETWORK_FILE = 'network.xml'
ORIGINAL_SCHEDULE = 'transitSchedule.xml.xml'
MARATHON_LINK_IDS_FILE = 'marathon_link_ids.txt'  # Note: Make sure filename is correct
AFFECTED_ROUTES_FILE = 'affected_routes.txt'
MODIFIED_SCHEDULE_FILE = 'transitSchedule_detour_auto.xml'
REPORT_FILE = 'detour_report.txt'  # 新增的报告文件名

print("\n--- 自动化脚本 (V5 - 修复XML结构): 开始 ---")

# 1. 加载数据 (代码不变)
with open(MARATHON_LINK_IDS_FILE, 'r') as f:
    marathon_links_set = set(line.strip() for line in f)
with open(AFFECTED_ROUTES_FILE, 'r') as f:
    affected_routes = [line.strip().split(',') for line in f]

# 2. 构建路网图 (代码不变)
print("正在构建路网图...")
G = nx.DiGraph()
parser = etree.XMLParser(remove_blank_text=True)
net_tree = etree.parse(NETWORK_FILE, parser)
net_root = net_tree.getroot()
link_data = {}
node_to_link_map = {}
for link in net_root.iter('link'):
    link_id = link.get('id')
    from_node = link.get('from')
    to_node = link.get('to')
    length = float(link.get('length', 1))
    freespeed = float(link.get('freespeed', 1))
    travel_time = length / freespeed
    link_data[link_id] = {'from': from_node, 'to': to_node}
    node_to_link_map[(from_node, to_node)] = link_id
    if link_id not in marathon_links_set:
        G.add_edge(from_node, to_node, weight=travel_time, link_id=link_id)
print(f"路网图构建完成。")

# 3. 解析公交时刻表并建立索引 (代码不变)
print("正在解析公交时刻表并建立索引...")
schedule_tree = etree.parse(ORIGINAL_SCHEDULE, parser)
schedule_root = schedule_tree.getroot()
route_id_to_element_map = {route.get('id'): route for route in schedule_root.iter('transitRoute')}
print("索引建立完成。")

# 4. 遍历每一条受影响的线路，应用新逻辑
print(f"开始为 {len(affected_routes)} 条路径应用绕行或取消策略...")
successful_detour_records, cancelled_route_records = [], []
successful_detours, cancelled_routes = 0, 0

for line_id, route_id in affected_routes:
    transit_route = route_id_to_element_map.get(route_id)
    if transit_route is None: continue

    parent_of_route = transit_route.getparent()
    original_links_elements = transit_route.find('route').findall('link')
    original_link_ids = [link.get('refId') for link in original_links_elements]

    first_closed_idx, last_closed_idx = -1, -1
    for i, link_id in enumerate(original_link_ids):
        if link_id in marathon_links_set:
            if first_closed_idx == -1: first_closed_idx = i
            last_closed_idx = i

    if first_closed_idx == -1 or first_closed_idx == 0 or last_closed_idx == len(original_link_ids) - 1:
        reason = "Starts/Ends within closure zone or no closure point found"
        cancelled_route_records.append(f"Line: {line_id}, Route: {route_id}, Reason: {reason}")
        parent_of_route.remove(transit_route)
        cancelled_routes += 1
        continue

    start_node = link_data[original_link_ids[first_closed_idx - 1]]['to']
    end_node = link_data[original_link_ids[last_closed_idx + 1]]['from']

    try:
        detour_node_path = nx.shortest_path(G, source=start_node, target=end_node, weight='weight')
        detour_link_ids = [node_to_link_map[(detour_node_path[i], detour_node_path[i + 1])] for i in
                           range(len(detour_node_path) - 1)]
        new_route_link_ids = original_link_ids[:first_closed_idx] + detour_link_ids + original_link_ids[
                                                                                      last_closed_idx + 1:]

        # --- **核心修正部分** ---
        new_route_id = route_id + "_detour"
        new_transit_route = etree.Element('transitRoute', id=new_route_id)

        # 1. 遍历旧route的所有子元素，保持原有顺序
        for child in transit_route:
            # 2. 如果不是<route>标签，就直接复制过来
            if child.tag != 'route':
                new_transit_route.append(child)
            # 3. 如果是<route>标签，就创建我们自己的新<route>标签替换它
            else:
                route_element = etree.SubElement(new_transit_route, 'route')
                for link_id in new_route_link_ids:
                    etree.SubElement(route_element, 'link', refId=link_id)

        # 4. 最后，用我们完整构建好的新route，替换掉旧的
        parent_of_route.replace(transit_route, new_transit_route)

        successful_detour_records.append(f"Line: {line_id}, Route: {route_id}, New Route ID: {new_route_id}")
        successful_detours += 1

    except nx.NetworkXNoPath:
        reason = f"No detour path found between nodes {start_node} and {end_node}"
        cancelled_route_records.append(f"Line: {line_id}, Route: {route_id}, Reason: {reason}")
        parent_of_route.remove(transit_route)
        cancelled_routes += 1
    except Exception as e:
        reason = f"An unexpected error occurred: {e}"
        cancelled_route_records.append(f"Line: {line_id}, Route: {route_id}, Reason: {reason}")
        parent_of_route.remove(transit_route)
        cancelled_routes += 1

# 5. 保存和报告 (代码不变)
schedule_tree.write(MODIFIED_SCHEDULE_FILE, pretty_print=True, xml_declaration=True, encoding='UTF-8')
print(f"\n正在生成详细报告文件: '{REPORT_FILE}'...")
with open(REPORT_FILE, 'w', encoding='utf-8') as f:
    # ... (省略报告内容)
    f.write("--- Detour and Cancellation Report ---\n\n")
    f.write(f"Summary: \n")
    f.write(f"  - Successfully Detoured Routes: {len(successful_detour_records)}\n")
    f.write(f"  - Cancelled Routes: {len(cancelled_route_records)}\n")
    f.write(f"  - Total Affected Routes Processed: {len(affected_routes)}\n\n")
    f.write(f"--- Successfully Detoured Routes ({len(successful_detour_records)}) ---\n")
    if successful_detour_records:
        for record in successful_detour_records: f.write(f"{record}\n")
    else:
        f.write("None\n")
    f.write(f"\n--- Cancelled Routes ({len(cancelled_route_records)}) ---\n")
    if cancelled_route_records:
        for record in cancelled_route_records: f.write(f"{record}\n")
    else:
        f.write("None\n")
print("报告文件生成完毕。")
print("\n--- 脚本执行完毕 ---")
print(f"成功生成绕行路径: {successful_detours} 条")
print(f"无法绕行而被取消的路径: {cancelled_routes} 条")
