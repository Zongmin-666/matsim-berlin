# modify_network.py

from lxml import etree

# --- 文件配置 ---
ORIGINAL_NETWORK_FILE = 'network.xml'
LINK_IDS_FILE ='marathon_link_ids.txt'
MODIFIED_NETWORK_FILE = 'network_fully_closed.xml'

print("\n--- 第一部分，步骤2：开始生成封路网络文件 ---")

with open(LINK_IDS_FILE, 'r') as f:
    link_ids_to_modify = set(line.strip() for line in f)

tree = etree.parse(ORIGINAL_NETWORK_FILE)
root = tree.getroot()

modified_count = 0
for link in root.xpath("//links/link"):
    if link.get('id') in link_ids_to_modify:
        link.set('freespeed', '0.1') # 降速法，模拟完全封锁
        modified_count += 1

tree.write(MODIFIED_NETWORK_FILE, pretty_print=True, xml_declaration=True, encoding='UTF-8')
print(f"封路网络生成完成！共修改 {modified_count} 个路段，新文件保存为 {MODIFIED_NETWORK_FILE}")