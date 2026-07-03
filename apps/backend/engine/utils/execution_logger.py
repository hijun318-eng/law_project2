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
    def __init__(self, question: str):
        self.question = question
        self.nodes = []  # list of dict: {"node": str, "elapsed_seconds": float, "status": str, "timestamp": str}
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


def init_logger(question: str) -> QueryLogger:
    """Initialize a new QueryLogger for the given question and set it as the active logger."""
    logger = QueryLogger(question)
    _logger_context.set(logger)
    return logger


def get_logger() -> QueryLogger | None:
    """Get the currently active QueryLogger, or None if none is active."""
    return _logger_context.get()


def clear_logger():
    """Clear the active logger."""
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
