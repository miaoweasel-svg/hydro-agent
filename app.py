"""Streamlit interface for the Hydro Agent demo."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parent
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from hydro_agent.agent import HydroAnalysisAgent  # noqa: E402
from hydro_agent.analysis import METRIC_LABELS, detect_anomalies, load_operation_data  # noqa: E402
from hydro_agent.config import settings  # noqa: E402
from hydro_agent.llm import OpenAIResponsesProvider  # noqa: E402
from hydro_agent.rag import (  # noqa: E402
    DenseVectorStore,
    OpenAIEmbeddingProvider,
    RAGService,
)

st.set_page_config(
    page_title="Hydro Agent | 水利工程运行分析",
    page_icon="💧",
    layout="wide",
)

st.markdown(
    """
    <style>
    .stApp { background: #f4f8fb; }
    [data-testid="stMetric"] {
        background: white; border: 1px solid #dce8ef; border-radius: 12px;
        padding: 14px 16px; box-shadow: 0 3px 12px rgba(23, 67, 89, .05);
    }
    .hero {
        padding: 1.2rem 1.4rem; border-radius: 14px;
        background: linear-gradient(110deg, #083b55, #0a6f78); color: white;
        margin-bottom: 1rem;
    }
    .hero h1 { margin: 0; font-size: 2rem; }
    .hero p { margin: .45rem 0 0; opacity: .86; }
    .safe-note {
        border-left: 4px solid #e6a23c; background: #fff9ec; padding: .7rem 1rem;
        border-radius: 7px; color: #5b4930; margin-bottom: 1rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data(show_spinner=False)
def load_demo_data(path: str) -> pd.DataFrame:
    return load_operation_data(path)


def build_rag() -> tuple[RAGService, str, str | None]:
    warning = None
    mode = "本地 TF-IDF"
    if settings.rag_embedding_provider.lower() == "openai" and settings.openai_api_key:
        try:
            embedding = OpenAIEmbeddingProvider(
                settings.openai_api_key, settings.openai_embedding_model
            )
            service = RAGService(DenseVectorStore(embedding))
            service.ingest_directory(settings.knowledge_dir)
            return service, f"OpenAI / {settings.openai_embedding_model}", None
        except Exception as exc:
            warning = f"OpenAI Embedding 初始化失败，已回退本地索引：{exc}"
    elif settings.rag_embedding_provider.lower() == "openai":
        warning = "RAG_EMBEDDING_PROVIDER=openai，但未配置 API Key；已回退本地索引。"
    service = RAGService()
    service.ingest_directory(settings.knowledge_dir)
    return service, mode, warning


def build_llm_provider() -> OpenAIResponsesProvider | None:
    if not settings.openai_api_key:
        return None
    try:
        return OpenAIResponsesProvider(settings.openai_api_key, settings.openai_model)
    except RuntimeError:
        return None


def line_chart(
    frame: pd.DataFrame, columns: list[str], title: str, y_title: str, colors: list[str]
) -> go.Figure:
    figure = go.Figure()
    for column, color in zip(columns, colors, strict=True):
        figure.add_trace(
            go.Scatter(
                x=frame["timestamp"],
                y=frame[column],
                mode="lines",
                name=METRIC_LABELS[column],
                line={"width": 2, "color": color},
                hovertemplate="%{x|%m-%d %H:%M}<br>%{y:.3f}<extra>%{fullData.name}</extra>",
            )
        )
    figure.update_layout(
        title=title,
        height=360,
        margin={"l": 20, "r": 20, "t": 55, "b": 20},
        paper_bgcolor="white",
        plot_bgcolor="white",
        hovermode="x unified",
        legend={"orientation": "h", "y": 1.12, "x": 0},
        xaxis={"title": "时间", "showgrid": False, "rangeslider": {"visible": False}},
        yaxis={"title": y_title, "gridcolor": "#edf2f5"},
    )
    return figure


def show_tool_trace(tool_calls: list[object]) -> None:
    if not tool_calls:
        return
    with st.expander(f"Agent 执行过程 · {len(tool_calls)} 个 Tool", expanded=False):
        for index, call in enumerate(tool_calls, start=1):
            st.markdown(f"**{index}. `{call.name}`**")
            st.caption("调用参数")
            st.code(json.dumps(call.arguments, ensure_ascii=False, indent=2), language="json")
            st.caption("Python 工具结果")
            st.json(call.result, expanded=False)


if "rag_service" not in st.session_state:
    rag_service, rag_mode, rag_warning = build_rag()
    st.session_state.rag_service = rag_service
    st.session_state.rag_mode = rag_mode
    st.session_state.rag_warning = rag_warning
if "messages" not in st.session_state:
    st.session_state.messages = []

st.markdown(
    """
    <div class="hero">
      <h1>水利工程运行数据智能分析系统</h1>
      <p>LLM-based Intelligent Analysis System for Hydraulic Engineering Operation Data</p>
    </div>
    <div class="safe-note">
      当前内置运行数据与知识文档均为 <b>synthetic / simulated</b> 演示内容。
      系统仅用于数据分析与技术演示，不用于真实工程调度或安全决策。
    </div>
    """,
    unsafe_allow_html=True,
)

with st.sidebar:
    st.header("数据与配置")
    data_upload = st.file_uploader("上传运行数据", type=["csv", "xlsx", "xls"])
    st.caption("必需字段：timestamp、upstream_level、downstream_level、gate_opening、flow")
    st.divider()
    st.subheader("工程知识库")
    knowledge_uploads = st.file_uploader(
        "上传知识文档", type=["pdf", "txt", "md"], accept_multiple_files=True
    )
    for upload in knowledge_uploads:
        try:
            st.session_state.rag_service.ingest_bytes(upload.getvalue(), upload.name)
        except Exception as exc:
            st.error(f"{upload.name} 载入失败：{exc}")
    if st.session_state.rag_service.sources:
        st.caption("已载入文件")
        for source in st.session_state.rag_service.sources:
            st.markdown(f"- `{source}`")
        st.caption(f"共 {len(st.session_state.rag_service.chunks)} 个知识片段")
    else:
        st.info("知识库尚无文件。")
    st.caption(f"检索模式：{st.session_state.rag_mode}")
    if st.session_state.rag_warning:
        st.warning(st.session_state.rag_warning)
    st.divider()
    provider_label = (
        f"OpenAI / {settings.openai_model}" if settings.openai_api_key else "离线规则路由"
    )
    st.caption(f"Agent 模式：{provider_label}")

try:
    if data_upload is not None:
        data = load_operation_data(data_upload.getvalue(), data_upload.name)
        data_source = f"上传文件：{data_upload.name}"
    else:
        data = load_demo_data(str(settings.demo_data_path))
        data_source = "内置 synthetic 演示数据"
except Exception as exc:
    st.error(f"运行数据载入失败：{exc}")
    st.stop()

llm_provider = build_llm_provider()
agent = HydroAnalysisAgent(data, st.session_state.rag_service, llm_provider)
anomaly_summary = detect_anomalies(data, metrics=["upstream_level", "downstream_level", "flow"])

st.subheader("数据概览")
st.caption(
    f"{data_source} · {data['timestamp'].min():%Y-%m-%d %H:%M} 至 "
    f"{data['timestamp'].max():%Y-%m-%d %H:%M} · {len(data)} 条小时数据"
)
metric_columns = st.columns(5)
metric_columns[0].metric("平均上游水位", f"{data['upstream_level'].mean():.3f} m")
metric_columns[1].metric("最高上游水位", f"{data['upstream_level'].max():.3f} m")
metric_columns[2].metric("平均下游水位", f"{data['downstream_level'].mean():.3f} m")
metric_columns[3].metric("平均流量", f"{data['flow'].mean():.2f} m³/s")
metric_columns[4].metric("统计异常点", str(anomaly_summary["anomaly_count"]))

st.subheader("运行数据可视化")
water_tab, gate_tab, flow_tab, table_tab = st.tabs(
    ["水位", "闸门开度", "流量", "原始数据"]
)
with water_tab:
    st.plotly_chart(
        line_chart(
            data,
            ["upstream_level", "downstream_level"],
            "上下游水位时间序列",
            "水位（m）",
            ["#087f8c", "#5b7cfa"],
        ),
        width="stretch",
    )
with gate_tab:
    st.plotly_chart(
        line_chart(data, ["gate_opening"], "闸门开度时间序列", "开度（%）", ["#d97706"]),
        width="stretch",
    )
with flow_tab:
    st.plotly_chart(
        line_chart(data, ["flow"], "流量时间序列", "流量（m³/s）", ["#0f766e"]),
        width="stretch",
    )
with table_tab:
    st.dataframe(data, width="stretch", hide_index=True)

assistant_column, report_column = st.columns([2, 1], gap="large")
with assistant_column:
    st.subheader("AI 运行分析助手")
    st.caption("示例：分析8月2日上游水位变化；检测异常水位；根据运行规程说明关注指标。")
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            if message["role"] == "assistant":
                show_tool_trace(message.get("tool_calls", []))
    question = st.chat_input("请输入运行数据或知识库问题")
    if question:
        st.session_state.messages.append({"role": "user", "content": question})
        with st.chat_message("user"):
            st.markdown(question)
        with st.chat_message("assistant"):
            with st.spinner("Agent 正在选择并执行分析工具…"):
                response = agent.ask(question)
            if response.warning:
                st.warning(response.warning)
            st.markdown(response.answer)
            show_tool_trace(response.tool_calls)
        st.session_state.messages.append(
            {
                "role": "assistant",
                "content": response.answer,
                "tool_calls": response.tool_calls,
            }
        )

with report_column:
    st.subheader("自动运行日报")
    st.write("基于当前数据生成可下载的 Markdown 分析报告。")
    if st.button("生成运行日报", type="primary", width="stretch"):
        report_response = agent.ask("生成一份运行情况日报")
        report_markdown = report_response.tool_calls[0].result["markdown"]
        st.session_state.latest_report = report_markdown
        st.success("日报已由 Python 工具生成。")
        show_tool_trace(report_response.tool_calls)
    if "latest_report" in st.session_state:
        st.markdown(st.session_state.latest_report)
        st.download_button(
            "下载 Markdown 日报",
            st.session_state.latest_report,
            file_name="synthetic_operation_report.md",
            mime="text/markdown",
            width="stretch",
        )
