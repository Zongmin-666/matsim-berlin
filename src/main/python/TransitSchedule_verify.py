# verify_schedule_final.py (V6 - 绕行方案版)
import sys
from lxml import etree
import os
import re

# ... (顶部的配置和print_check函数保持不变) ...
ORIGINAL_SCHEDULE = 'transitSchedule.xml.xml'
MODIFIED_SCHEDULE = 'transitSchedule_detour_auto.xml'
REPORT_FILE = 'detour_report.txt'
error_count = 0
def print_check(message, status):
    global error_count
    if status: print(f"  ✅ [PASS] {message}")
    else:
        print(f"  ❌ [FAIL] {message}")
        error_count += 1
# --------------------------------------------------------

def validate_xml_schema(filepath):
    """使用lxml的DTD验证功能，检查XML文件是否符合MATSim的结构要求"""
    print(f"\n--- 1. 正在对 '{filepath}' 进行MATSim结构验证 (DTD Schema Check) ---")
    if not os.path.exists(filepath):
        print_check(f"文件不存在！", False)
        return False
    try:
        # --- **核心修改：换一种调用方式** ---
        # 1. 创建一个配置好DTD验证的解析器
        parser = etree.XMLParser(dtd_validation=True)
        # 2. 用这个解析器去解析文件
        etree.parse(filepath, parser=parser)
        # ------------------------------------
        print_check("文件结构和元素顺序符合MATSim官方要求。", True)
        return True
    except etree.XMLSyntaxError as e:
        print_check(f"文件结构存在严重错误！MATSim运行时会因此崩溃。", False)
        print(f"      详细错误: {e}")
        return False
    except TypeError as e:
        print_check(f"你环境中的lxml库似乎有深层问题，无法执行DTD验证: {e}", False)
        print("      跳过结构检查，继续进行内容审计...")
        return "SKIP" # 返回一个特殊值，表示跳过

# ... (后续的 compare_elements_recursively 和 run_final_verification 函数保持不变) ...
# 为了完整性，我将整个脚本都放在下面

def compare_elements_recursively(e1, e2):
    if e1.tag != e2.tag or e1.attrib != e2.attrib or len(e1) != len(e2) or (e1.text or '').strip() != (e2.text or '').strip():
        return False
    for c1, c2 in zip(e1, e2):
        if not compare_elements_recursively(c1, c2):
            return False
    return True

def run_final_verification():
    global error_count
    error_count = 0
    print("=====================================================")
    print("===   MATSim TransitSchedule 最终验证脚本启动   ===")
    print("=====================================================")
    is_original_ok = validate_xml_schema(ORIGINAL_SCHEDULE)
    is_modified_ok = validate_xml_schema(MODIFIED_SCHEDULE)
    if not is_modified_ok and is_modified_ok != "SKIP":
        print("\n由于修改后的文件结构验证失败，后续内容检查可能无意义。请先修复结构问题。")
        return
    print(f"\n--- 2. 正在进行内容审计：比较 '{ORIGINAL_SCHEDULE}' 和 '{MODIFIED_SCHEDULE}' ---")
    try:
        successfully_detoured_ids = set()
        cancelled_ids = set()
        with open(REPORT_FILE, 'r', encoding='utf-8') as f:
            mode = None
            for line in f:
                if "--- Successfully Detoured Routes" in line: mode = 'detoured'
                elif "--- Cancelled Routes" in line: mode = 'cancelled'
                match = re.search(r"Route: (.+?),", line)
                if match:
                    if mode == 'detoured': successfully_detoured_ids.add(match.group(1))
                    elif mode == 'cancelled': cancelled_ids.add(match.group(1))
        print_check(f"成功解析报告: {len(successfully_detoured_ids)}条绕行, {len(cancelled_ids)}条取消。", True)
        original_routes = {route.get('id'): route for route in etree.parse(ORIGINAL_SCHEDULE).getroot().iter('transitRoute')}
        modified_routes = {route.get('id'): route for route in etree.parse(MODIFIED_SCHEDULE).getroot().iter('transitRoute')}
        print_check("成功建立新旧文件的内容索引。", True)
    except Exception as e:
        print_check(f"加载报告或建立索引时出错: {e}", False)
        return
    print("\n--- 2.1 验证【已修改】的部分是否按预期执行 ---")
    for route_id in successfully_detoured_ids:
        detour_id = f"{route_id}_detour"
        check1 = route_id not in modified_routes
        print_check(f"绕行线路 '{route_id}': 旧路径已按预期删除。", check1)
        check2 = detour_id in modified_routes
        print_check(f"绕行线路 '{route_id}': 新的绕行路径 '{detour_id}' 已按预期创建。", check2)
    for route_id in cancelled_ids:
        check1 = route_id not in modified_routes
        print_check(f"取消线路 '{route_id}': 旧路径已按预期删除。", check1)
        detour_id = f"{route_id}_detour"
        check2 = detour_id not in modified_routes
        print_check(f"取消线路 '{route_id}': 确认没有创建绕行路径。", check2)
    print("\n--- 2.2 验证【未修改】的部分是否保持完全一致 ---")
    unaffected_errors = 0
    for route_id, original_element in original_routes.items():
        if route_id not in successfully_detoured_ids and route_id not in cancelled_ids:
            modified_element = modified_routes.get(route_id)
            if modified_element is None:
                print_check(f"未受影响的路径 '{route_id}' 在新文件中丢失！", False)
                unaffected_errors += 1
            else:
                if not compare_elements_recursively(original_element, modified_element):
                    print_check(f"未受影响的路径 '{route_id}' 内容被意外修改！", False)
                    unaffected_errors += 1
    if unaffected_errors == 0:
        print_check("所有未受影响的公交路径均保持原始状态，完全一致。", True)
    print("\n=====================================================")
    print("===                     最终总结                   ===")
    print("=====================================================")
    if error_count == 0:
        print("\n✅✅✅ 祝贺你！所有检查点均已通过！✅✅✅")
        print("你的 `transitSchedule_detour_auto.xml` 文件在结构上和内容上都是准确无误的。")
    else:
        print(f"\n❌❌❌ 检查失败！共发现 {error_count} 个问题。❌❌❌")
        print("  请检查上面标记为 [FAIL] 的项目。")
    print("\n")

if __name__ == "__main__":
    run_final_verification()