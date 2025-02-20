import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Callable, TypeVar, Generic, Any
from dataclasses import dataclass
from app.config.config import thread_config

T = TypeVar('T')
R = TypeVar('R')

@dataclass
class ThreadTask(Generic[T]):
    """Класс для хранения задачи и её данных"""
    data: T
    task_id: str

class ThreadManager:
    """Менеджер потоков для параллельной обработки задач"""
    
    def __init__(self, max_workers: int = None):
        self.max_workers = max_workers or thread_config.MAX_THREADS
        self._lock = threading.Lock()
        
    def process_tasks(self, tasks: List[ThreadTask[T]], worker_func: Callable[[ThreadTask[T]], R]) -> List[R]:
        """
        Обрабатывает список задач параллельно
        
        Args:
            tasks: Список задач для обработки
            worker_func: Функция-обработчик для каждой задачи
            
        Returns:
            List[R]: Список результатов обработки
        """
        results = []
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_task = {
                executor.submit(self._safe_worker, worker_func, task): task
                for task in tasks
            }
            
            for future in as_completed(future_to_task):
                task = future_to_task[future]
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    print(f"Ошибка при обработке задачи {task.task_id}: {str(e)}")
                    
        return results
    
    def _safe_worker(self, worker_func: Callable[[ThreadTask[T]], R], task: ThreadTask[T]) -> R:
        """
        Безопасно выполняет функцию-обработчик с использованием блокировки
        
        Args:
            worker_func: Функция-обработчик
            task: Задача для обработки
            
        Returns:
            R: Результат обработки
        """
        with self._lock:
            return worker_func(task)
