import time
import json
import os
import functools
import contextvars
from datetime import datetime
from pathlib import Path


__all__ = ["QueryLogger", "log_node", "init_logger", "get_logger", "clear_logger"]

_logger_context: contextvars.ContextVar = contextvars.ContextVar("query_logger", default=None)


class QueryLogger:
    def __init__(self, question: str, session_id: str | None = None):
        self.question = question
        self.session_id = session_id
        self.nodes = []  # list of dict: {"node": str, "elapsed_seconds": float, "status": str, "timestamp": str}
        self.llm_usages = []  # list of dict: LLM/embedding API call usage
        self.start_time = time.time()
        self.start_timestamp = datetime.now().isoformat()
        self.end_time = None
        self.end_timestamp = None
        self.answer = ""

    def record_node(self, node_name: str, elapsed: float, status: str = "success"):
        """Record timing for one node execution"""
        self.nodes.append({
            "node": node_name,
            "elapsed_seconds": round(elapsed, 6),
            "status": status,
            "timestamp": datetime.now().isoformat()
        })

    def record_llm_usage(self, node_name: str, model: str, call_type: str = "llm",
                         prompt_tokens: int = 0, completion_tokens: int = 0,
                         total_tokens: int = 0):
        """Record LLM/embedding API call usage"""
        self.llm_usages.append({
            "node_name": node_name,
            "model": model,
            "call_type": call_type,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
            "timestamp": datetime.now().isoformat(),
        })

    def finish(self, answer: str):
        """Mark query as finished with final answer"""
        self.end_time = time.time()
        self.end_timestamp = datetime.now().isoformat()
        self.answer = answer

    def total_elapsed(self) -> float:
        """Total elapsed time in seconds"""
        end = self.end_time or time.time()
        return round(end - self.start_time, 6)

    def save(self, log_dir: str | None = None) -> str:
        """Save log as JSON file to temp/logs/ directory. Returns the file path."""
        if log_dir is None:
            # Calculate path relative to this file: engine/utils/ -> project_root/temp/logs/
            log_dir = os.path.join(Path(__file__).resolve().parents[2], "temp", "logs")
        os.makedirs(log_dir, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = os.path.join(log_dir, f"{ts}.json")
        data = {
            "timestamp": datetime.now().isoformat(),
            "start_timestamp": self.start_timestamp,
            "end_timestamp": self.end_timestamp,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "question": self.question,
            "total_elapsed_seconds": self.total_elapsed(),
            "nodes": self.nodes,
            "answer_preview": (self.answer[:500] + "...") if len(self.answer) > 500 else self.answer,
        }
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Warning: Failed to save log: {e}")
        return filepath

    def save_db(self) -> int:
        """Save node execution logs and LLM usage logs to DB via bulk_create. Returns total records saved."""
        from monitoring.models import NodeExecutionLog, LLMUsageLog

        total = 0
        try:
            # NodeExecutionLog bulk_create
            node_objs = [
                NodeExecutionLog(
                    session_id=self.session_id or "",
                    node_name=n["node"],
                    elapsed_ms=n["elapsed_seconds"] * 1000,  # 초 → ms 변환
                    status=n["status"],
                    created_at=datetime.fromisoformat(n["timestamp"]) if isinstance(n["timestamp"], str) else n["timestamp"],
                )
                for n in self.nodes
            ]
            if node_objs:
                NodeExecutionLog.objects.bulk_create(node_objs)
                total += len(node_objs)

            # LLMUsageLog bulk_create
            llm_objs = [
                LLMUsageLog(
                    session_id=self.session_id or "",
                    node_name=u["node_name"],
                    model=u["model"],
                    call_type=u["call_type"],
                    prompt_tokens=u["prompt_tokens"],
                    completion_tokens=u["completion_tokens"],
                    total_tokens=u["total_tokens"],
                    created_at=datetime.fromisoformat(u["timestamp"]) if isinstance(u["timestamp"], str) else u["timestamp"],
                )
                for u in self.llm_usages
            ]
            if llm_objs:
                LLMUsageLog.objects.bulk_create(llm_objs)
                total += len(llm_objs)
        except Exception as e:
            print(f"Warning: Failed to save to DB: {e}")
            return 0
        return total


def init_logger(question: str, session_id: str | None = None) -> QueryLogger:
    """Initialize a new QueryLogger for the given question and set it as the active logger."""
    logger = QueryLogger(question, session_id=session_id)
    _logger_context.set(logger)
    return logger


def get_logger() -> QueryLogger | None:
    """Get the currently active QueryLogger, or None if none is active."""
    return _logger_context.get()


def clear_logger():
    """Clear the active logger. If there are unsaved data, try saving to DB first."""
    logger = get_logger()
    if logger and (logger.nodes or logger.llm_usages):
        try:
            logger.save_db()
        except Exception:
            pass
    _logger_context.set(None)


def log_node(func):
    """Decorator that measures execution time of a LangGraph node function and records it to the active logger."""
    @functools.wraps(func)
    def wrapper(state, *args, **kwargs):
        logger = get_logger()
        node_name = func.__name__.replace("_node", "")
        start = time.time()
        try:
            result = func(state, *args, **kwargs)
            elapsed = time.time() - start
            if logger:
                logger.record_node(node_name, elapsed, "success")
            return result
        except Exception as e:
            elapsed = time.time() - start
            if logger:
                logger.record_node(node_name, elapsed, f"error: {str(e)}")
            raise
    return wrapper
