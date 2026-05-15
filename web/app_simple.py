"""Dredactor Web 界面 - Streamlit (简化版)"""

import os
import sys
import tempfile
from pathlib import Path

import streamlit as st

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dredactor import (
    DocumentParser,
    RedactionEngine,
    DocumentExporter,
    ReportGenerator,
    RuleManager,
    load_rules,
    RedactionMapper,
    create_mapper,
    generate_report,
)

# Streamlit 配置
st.set_page_config(
    page_title="Dredactor - Word 文档脱敏",
    page_icon="🔒",
    layout="wide",
    initial_sidebar_state="expanded",
)

# 自定义 CSS
st.markdown("""
<style>
    .stApp {
        max-width: 1200px;
    }
    .stButton[kind="primary"] {
        background-color: #FF4B4B;
    }
    .upload-success {
        background-color: #d4edda;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 1rem 0;
    }
    .download-box {
        background-color: #e0f2fe;
        padding: 1.5rem;
        border-radius: 0.5rem;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

# 工具函数
def find_mapping_file(redacted_filename):
    mapping_dir = Path('.mappings')
    if not mapping_dir.exists():
        return None
    if '_redacted_' in redacted_filename:
        parts = redacted_filename.split('_redacted_')
        if len(parts) == 2:
            map_id = Path(parts[1]).stem
            mapping_file = mapping_dir / f'{map_id}.json'
            if mapping_file.exists():
                return mapping_file
    return None

# 侧边栏
with st.sidebar:
    st.title("Dredactor")
    st.markdown("---")
    page = st.radio(
        "选择功能",
        ["文档脱敏", "文档恢复", "规则管理", "关于"],
        label_visibility="collapsed",
    )
    st.markdown("---")
    with st.expander("规则统计"):
        if "rule_manager" not in st.session_state:
            st.session_state.rule_manager = load_rules()
        rule_manager = st.session_state.rule_manager
        all_rules = rule_manager.get_all_rules()
        enabled_rules = rule_manager.get_enabled_rules()
        st.metric("总规则数", len(all_rules))
        st.metric("已启用", len(enabled_rules))
        st.metric("已禁用", len(all_rules) - len(enabled_rules))
    st.markdown("---")
    if st.button("重新加载规则"):
        st.cache_data.clear()
        st.rerun()

# 主内容
if page == "文档脱敏":
    st.header("文档脱敏")
    uploaded_file = st.file_uploader("上传 Word 文档", type=['docx'])
    if uploaded_file:
        col1, col2, col3 = st.columns(3)
        with col1:
            strategy = st.selectbox(
                "脱敏策略",
                options=["replace", "mask", "partial", "company"],
                index=0,
                help="replace: 替换(可恢复), mask: 遮蔽(不可恢复), partial: 部分显示(不可恢复), company: 公司名称(不可恢复)"
            )
        with col2:
            replacement = st.text_input(
                "替换文本",
                value="[已脱敏]",
                disabled=(strategy != "replace"),
            )
        with col3:
            override_strategy = st.checkbox(
                "覆盖规则默认策略",
                value=False,
                help="启用后将使用全局策略，忽略规则的默认策略"
            )
        st.markdown("---")
        save_map = st.checkbox(
            "保存脱敏映射（用于后续恢复）",
            value=True,
            help="保存后可编辑脱敏文档，再恢复原始信息"
        )
        if st.button("执行脱敏", type="primary"):
            with st.spinner("正在处理文档..."):
                try:
                    with tempfile.NamedTemporaryFile(delete=False, suffix='.docx') as tmp_file:
                        tmp_file.write(uploaded_file.read())
                        tmp_file.flush()
                        parser = DocumentParser()
                        parsed_doc = parser.parse(tmp_file.name)
                        rule_manager = load_rules()
                        engine = RedactionEngine(
                            rules=rule_manager.get_enabled_rules(),
                            default_strategy=strategy,
                            replacement_text=replacement,
                            override_strategy=override_strategy,
                        )
                        result = engine.redact_document(parsed_doc)
                        if save_map:
                            mapper = create_mapper()
                            map_id = mapper.generate_map_id()
                            map_data = mapper.create_map(
                                map_id=map_id,
                                source_file=uploaded_file.name,
                                redacted_file="",
                                records=result.stats.records,
                            )
                            redacted_doc = mapper.apply_markers_to_document(result.redacted_doc, map_data)
                            base = os.path.splitext(uploaded_file.name)[0]
                            output_filename = f"{base}_redacted_{map_id}.docx"
                            map_data.redacted_file = output_filename
                            mapper.save_map(map_data)
                            exporter = DocumentExporter()
                            exporter.export(redacted_doc, output_filename, overwrite=True)
                            st.session_state['last_output_file'] = output_filename
                            st.session_state['last_mapping_file'] = os.path.join(mapper.MAPPINGS_DIR, f'{map_id}.json')
                            st.session_state['last_output_filename'] = output_filename
                            st.session_state['map_id'] = map_id
                        else:
                            base = os.path.splitext(uploaded_file.name)[0]
                            output_filename = f"{base}_redacted.docx"
                            exporter = DocumentExporter()
                            exporter.export(result.redacted_doc, output_filename, overwrite=True)
                            st.session_state['last_output_file'] = output_filename
                            st.session_state['last_output_filename'] = output_filename
                        st.session_state['last_result'] = result
                        st.session_state['last_upload_filename'] = uploaded_file.name
                    st.success("脱敏完成！")
                except Exception as e:
                    st.error(f"处理失败：{str(e)}")
        if 'last_result' in st.session_state:
            result = st.session_state['last_result']
            st.markdown('<div class="upload-success">', unsafe_allow_html=True)
            st.subheader("处理结果")
            col1, col2 = st.columns(2)
            col1.metric("脱敏总数", result.stats.total_redacted)
            col2.metric("处理时间", f"{result.stats.processing_time:.3f} 秒")
            if result.stats.rules_used:
                st.markdown("#### 规则使用情况")
                for rule_name, count in sorted(result.stats.rules_used.items()):
                    st.write(f"- {rule_name}: {count} 处")
            st.markdown('</div>', unsafe_allow_html=True)
            st.markdown('<div class="download-box">', unsafe_allow_html=True)
            st.markdown("#### 下载文件")
            with open(st.session_state['last_output_file'], 'rb') as f:
                st.download_button(
                    data=f.read(),
                    file_name=st.session_state['last_output_filename'],
                    mime='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                    label="下载脱敏文档",
                    type="primary",
                )
            if save_map and 'last_mapping_file' in st.session_state:
                st.markdown("##### 映射文件")
                st.info("映射文件用于后续恢复脱敏信息，请妥善保管。")
                with open(st.session_state['last_mapping_file'], 'rb') as f:
                    st.download_button(
                        data=f.read(),
                        file_name=f"mapping_{st.session_state['map_id']}.json",
                        mime='application/json',
                        label="下载映射文件",
                    )
            st.markdown('</div>', unsafe_allow_html=True)

elif page == "文档恢复":
    st.header("文档恢复")
    st.info("上传脱敏后的文档和映射文件，恢复原始敏感信息")
    col1, col2 = st.columns(2)
    with col1:
        redacted_file = st.file_uploader("上传脱敏文档", type=['docx'])
    with col2:
        mapping_file = st.file_uploader("上传映射文件（可选）", type=['json'])
    local_mapping_path = None
    if redacted_file:
        if '_redacted_' not in redacted_file.name:
            st.warning("文件名似乎不是脱敏文件格式（应包含 _redacted_）")
        if not mapping_file:
            local_mapping_path = find_mapping_file(redacted_file.name)
            if local_mapping_path:
                st.success(f"找到映射文件：{local_mapping_path.name}")
            else:
                st.error("未找到映射文件，请上传映射文件")
    if st.button("恢复文档", type="primary"):
        if not mapping_file and not local_mapping_path:
            st.error("请上传映射文件或使用标准文件名格式")
        else:
            with st.spinner("正在恢复文档..."):
                try:
                    with tempfile.NamedTemporaryFile(delete=False, suffix='.docx') as tmp_redacted:
                        tmp_redacted.write(redacted_file.read())
                        tmp_redacted.flush()
                    if mapping_file:
                        with tempfile.NamedTemporaryFile(delete=False, suffix='.json') as tmp_mapping:
                            tmp_mapping.write(mapping_file.read())
                            tmp_mapping.flush()
                            map_path = tmp_mapping.name
                    else:
                        map_path = str(local_mapping_path)
                    mapper = create_mapper()
                    output_file = tempfile.NamedTemporaryFile(delete=False, suffix='.docx')
                    restored_doc = mapper.restore_document(
                        redacted_file_path=tmp_redacted.name,
                        output_path=output_file.name,
                        map_path=map_path,
                    )
                    base = os.path.splitext(redacted_file.name)[0]
                    st.session_state['restored_output_file'] = output_file.name
                    st.session_state['restored_filename'] = f"{base}_restored.docx"
                    st.success("恢复完成！")
                except Exception as e:
                    st.error(f"恢复失败：{str(e)}")
        if 'restored_output_file' in st.session_state:
            st.markdown('<div class="download-box">', unsafe_allow_html=True)
            st.markdown("#### 下载恢复后的文档")
            with open(st.session_state['restored_output_file'], 'rb') as f:
                st.download_button(
                    data=f.read(),
                    file_name=st.session_state['restored_filename'],
                    mime='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                    label="下载恢复文档",
                    type="primary",
                )
            st.markdown('</div>', unsafe_allow_html=True)

elif page == "规则管理":
    st.header("规则管理")
    if "rule_manager" not in st.session_state:
        st.session_state.rule_manager = load_rules()
    rule_manager = st.session_state.rule_manager
    all_rules = rule_manager.get_all_rules()
    search = st.text_input("搜索规则", placeholder="输入规则名称或描述...")
    st.markdown("### 规则列表")
    filtered_rules = all_rules
    if search:
        filtered_rules = [r for r in all_rules if search.lower() in r.name.lower() or search.lower() in r.description.lower()]
    for rule in filtered_rules:
        with st.expander(f"{rule.name} - {rule.description}", expanded=False):
            col1, col2, col3 = st.columns(3)
            with col1:
                new_enabled = st.checkbox("启用", value=rule.enabled, key=f"enable_{rule.name}")
                if new_enabled != rule.enabled:
                    if new_enabled:
                        rule_manager.enable_rule(rule.name)
                    else:
                        rule_manager.disable_rule(rule.name)
                    st.rerun()
            with col2:
                st.selectbox(
                    "策略",
                    options=["mask", "replace", "partial", "company"],
                    index=["mask", "replace", "partial", "company"].index(rule.strategy),
                    key=f"strategy_{rule.name}",
                    disabled=True,
                )
            with col3:
                st.code(rule.pattern, language="regex")
            with st.expander("详细信息", expanded=False):
                st.json({
                    "name": rule.name,
                    "description": rule.description,
                    "pattern": rule.pattern,
                    "strategy": rule.strategy,
                    "priority": rule.priority,
                    "enabled": rule.enabled,
                    "replacement": rule.replacement,
                    "show_prefix": rule.show_prefix,
                    "show_suffix": rule.show_suffix,
                })

elif page == "关于":
    st.header("关于 Dredactor")
    col1, col2 = st.columns([2, 1])
    with col1:
        st.markdown("""
        ### Dredactor - Word 文档脱敏工具

        Dredactor 是一个强大的 Word 文档脱敏工具，支持基于规则和 AI 辅助的敏感信息识别与替换。

        **主要功能：**

        - 多种敏感信息识别规则（身份证、手机号、邮箱、银行卡等）
        - 灵活的脱敏模式（替换、遮蔽、部分显示）
        - 脱敏映射与恢复功能
        - 保留 Word 文档原始格式
        - 详细的脱敏报告生成

        **开发信息：**

        - Python 版本：3.9+
        - 主要依赖：python-docx, pytest, streamlit
        - 开源协议：MIT License
        """)
    with col2:
        st.info("当前版本：v0.1.0")
        st.markdown("""
        **GitHub 仓库：**
        [github.com/libraor/Dredactor](https://github.com/libraor/Dredactor)

        **报告问题：**
        [Issues](https://github.com/libraor/Dredactor/issues)
        """)

# 页脚
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666;'>
    <small>
        Dredactor Web 界面 |
        <a href='https://github.com/libraor/Dredactor' target='_blank'>GitHub</a> |
        Made with Streamlit
    </small>
</div>
""", unsafe_allow_html=True)
