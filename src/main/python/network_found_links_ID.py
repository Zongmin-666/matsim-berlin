# identify_links.py

import geopandas as gpd
from lxml import etree
from shapely.geometry import LineString, Point

GPX_LAYER = 'tracks'
SOURCE_CRS = 'EPSG:4326'  # GPX文件的原始坐标系（经纬度）
TARGET_CRS_EPSG = 25832  # network.xml文件明确指定的坐标系
# --- 文件配置 ---
NETWORK_FILE = 'network.xml'
ROUTE_FILE = 'marathon_route.gpx'
OUTPUT_LINK_IDS_FILE = 'marathon_link_ids.txt'


# --- 主程序 ---
print(f"--- 最终版：强制从 {SOURCE_CRS} 转换到 EPSG:{TARGET_CRS_EPSG} ---")

try:
    # 1. 读取GPX文件
    route_gdf = gpd.read_file(ROUTE_FILE, layer=GPX_LAYER)

    # 2. 强制设置其原始坐标系为WGS84 (EPSG:4326)
    #    这一步是关键，我们不再相信自动检测
    route_gdf = route_gdf.set_crs(SOURCE_CRS)
    print(f"已强制设定GPX原始坐标系为: {SOURCE_CRS}")

    # 3. 将其坐标系转换成和路网文件一致的目标坐标系
    route_gdf = route_gdf.to_crs(epsg=TARGET_CRS_EPSG)
    print(f"已成功将GPX坐标系转换为: EPSG:{TARGET_CRS_EPSG}")

    # 4. 创建缓冲区并进行匹配
    route_buffer = route_gdf.union_all().buffer(20)
    print("已创建路线缓冲区，正在匹配路段...")

    tree = etree.parse(NETWORK_FILE)
    nodes = {node.get('id'): (float(node.get('x')), float(node.get('y'))) for node in tree.xpath("//node")}

    matched_link_ids = []
    for link in tree.xpath("//link"):
        start_coords = nodes.get(link.get('from'))
        end_coords = nodes.get(link.get('to'))
        if start_coords and end_coords:
            if LineString([Point(start_coords), Point(end_coords)]).intersects(route_buffer):
                matched_link_ids.append(link.get('id'))

    with open(OUTPUT_LINK_IDS_FILE, 'w') as f:
        for link_id in matched_link_ids:
            f.write(f"{link_id}\n")

    print(f"\n识别完成！找到 {len(matched_link_ids)} 个需封锁路段。")
    if len(matched_link_ids) > 0:
        print("太棒了！问题已解决。现在可以继续进行后续步骤了。")
    else:
        print("警告：仍然没有找到匹配路段。这极不寻常，请务必使用QGIS进行可视化检查。")

except Exception as e:
    print(f"发生错误：{e}")