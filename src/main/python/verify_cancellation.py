# verify_cancellation.py
import sys
from lxml import etree
import os
import re

# --- 文件路径配置 ---
ORIGINAL_SCHEDULE = 'transitSchedule.xml.xml'
MODIFIED_SCHEDULE = 'transitSchedule_cancelled_only.xml'
AFFECTED_ROUTES_FILE = 'affected_routes.txt'

# --- 全局状态 ---
error_count = 0


def print_check(message, status):
    """一个统一的打印函数，显示状态和信息"""
    global error_count
    if status:
        print(f"  ✅ [PASS] {message}")
    else:
        print(f"  ❌ [FAIL] {message}")
        error_count += 1


def validate_xml_schema(filepath):
    """使用lxml的DTD验证功能，检查XML文件是否符合MATSim的结构要求"""
    print(f"\n--- 1. 正在对 '{filepath}' 进行MATSim结构验证 ---")
    if not os.path.exists(filepath):
        print_check(f"文件不存在！", False)
        return False
    try:
        # 提醒：如果此步失败并提示网络错误，请确保 transitSchedule_v2.dtd 文件在本地
        parser = etree.XMLParser(dtd_validation=True)
        etree.parse(filepath, parser=parser)
        print_check("文件结构和元素顺序符合MATSim官方要求。", True)
        return True
    except etree.XMLSyntaxError as e:
        print_check(f"文件结构存在严重错误！MATSim运行时会因此崩溃。", False)
        print(f"      详细错误: {e}")
        return False


def compare_elements_recursively(e1, e2):
    """递归地、深度地比较两个XML元素的内容和结构是否完全一致"""
    if e1.tag != e2.tag or e1.attrib != e2.attrib or len(e1) != len(e2) or (e1.text or '').strip() != (
            e2.text or '').strip():
        return False
    for c1, c2 in zip(e1, e2):
        if not compare_elements_recursively(c1, c2):
            return False
    return True


def run_final_verification():
    global error_count
    error_count = 0

    print("=====================================================")
    print("===      ‘取消策略’ TransitSchedule 验证脚本      ===")
    print("=====================================================")

    # 步骤一：结构验证
    validate_xml_schema(MODIFIED_SCHEDULE)
    if error_count > 0:
        print("\n由于修改后的文件结构验证失败，后续内容检查可能无意义。")
        return

    # 步骤二：内容审计
    print(f"\n--- 2. 正在进行内容审计 ---")
    try:
        with open(AFFECTED_ROUTES_FILE, 'r') as f:
            affected_route_ids = {line.strip().split(',')[1] for line in f}
        print_check(f"成功解析报告: 共有 {len(affected_route_ids)} 条线路应被取消。", True)

        original_routes = {route.get('id'): route for route in
                           etree.parse(ORIGINAL_SCHEDULE).getroot().iter('transitRoute')}
        modified_routes = {route.get('id'): route for route in
                           etree.parse(MODIFIED_SCHEDULE).getroot().iter('transitRoute')}
        print_check("成功建立新旧文件的内容索引。", True)
    except Exception as e:
        print_check(f"加载报告或建立索引时出错: {e}", False)
        return

    # 2.1 验证【应被删除】的线路是否真的消失了
    print("\n--- 2.1 验证【应被删除】的线路 ---")
    deleted_routes_ok = True
    for route_id in affected_route_ids:
        if route_id in modified_routes:
            print_check(f"线路 '{route_id}' 本应被删除，但仍存在于新文件中！", False)
            deleted_routes_ok = False
    if deleted_routes_ok:
        print_check("所有受影响的线路均已按预期被成功删除。", True)

    # 2.2 验证【未受影响】的线路是否保持完全一致
    print("\n--- 2.2 验证【未受影响】的线路 ---")
    unaffected_errors = 0
    for route_id, original_element in original_routes.items():
        if route_id not in affected_route_ids:
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

    # --- 最终总结 ---
    print("\n=====================================================")
    print("===                     最终总结                   ===")
    print("=====================================================")
    if error_count == 0:
        print("\n✅✅✅ 祝贺你！所有检查点均已通过！✅✅✅")
        print("你的 `transitSchedule_cancelled_only.xml` 文件准确无误。")
    else:
        print(f"\n❌❌❌ 检查失败！共发现 {error_count} 个问题。❌❌❌")
        print("  请检查上面标记为 [FAIL] 的项目。")
    print("\n")


if __name__ == "__main__":
    run_final_verification()