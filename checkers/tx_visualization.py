# -*- coding: utf-8 -*-
"""
Transaction Visualization v1.0.60
Визуализация транзакций и денежных потоков
"""

import asyncio
import aiohttp
from typing import Dict, Any, Optional, List, Set, Tuple
from datetime import datetime
from collections import defaultdict


class TransactionGraph:
    """Граф транзакций"""
    
    def __init__(self):
        self.nodes = {}  # address -> node_data
        self.edges = []  # (from, to, value, tx_hash)
    
    def add_node(self, address: str, label: Optional[str] = None):
        """Добавить узел"""
        
        if address not in self.nodes:
            self.nodes[address] = {
                "address": address,
                "label": label or f"{address[:6]}...{address[-4:]}",
                "in_degree": 0,
                "out_degree": 0,
                "total_in": 0.0,
                "total_out": 0.0,
            }
    
    def add_edge(
        self,
        from_addr: str,
        to_addr: str,
        value: float,
        tx_hash: str
    ):
        """Добавить ребро"""
        
        self.add_node(from_addr)
        self.add_node(to_addr)
        
        self.edges.append({
            "from": from_addr,
            "to": to_addr,
            "value": value,
            "tx_hash": tx_hash,
        })
        
        # Обновляем степени
        self.nodes[from_addr]["out_degree"] += 1
        self.nodes[from_addr]["total_out"] += value
        self.nodes[to_addr]["in_degree"] += 1
        self.nodes[to_addr]["total_in"] += value
    
    def get_neighbors(self, address: str, direction: str = "both") -> List[str]:
        """Получить соседей узла"""
        
        neighbors = set()
        
        for edge in self.edges:
            if direction in ["out", "both"] and edge["from"] == address:
                neighbors.add(edge["to"])
            if direction in ["in", "both"] and edge["to"] == address:
                neighbors.add(edge["from"])
        
        return list(neighbors)
    
    def get_subgraph(
        self,
        center: str,
        depth: int = 1
    ) -> "TransactionGraph":
        """Получить подграф вокруг узла"""
        
        subgraph = TransactionGraph()
        visited = set()
        queue = [(center, 0)]
        
        while queue:
            node, current_depth = queue.pop(0)
            
            if node in visited or current_depth > depth:
                continue
            
            visited.add(node)
            
            # Добавляем узел
            if node in self.nodes:
                node_data = self.nodes[node]
                subgraph.add_node(node, node_data.get("label"))
            
            # Добавляем ребра
            for edge in self.edges:
                if edge["from"] == node or edge["to"] == node:
                    subgraph.add_edge(
                        edge["from"],
                        edge["to"],
                        edge["value"],
                        edge["tx_hash"]
                    )
                    
                    # Добавляем соседей в очередь
                    if current_depth < depth:
                        if edge["from"] == node:
                            queue.append((edge["to"], current_depth + 1))
                        if edge["to"] == node:
                            queue.append((edge["from"], current_depth + 1))
        
        return subgraph
    
    def find_paths(
        self,
        start: str,
        end: str,
        max_depth: int = 5
    ) -> List[List[str]]:
        """Найти пути между узлами"""
        
        paths = []
        
        def dfs(current: str, target: str, path: List[str], depth: int):
            if depth > max_depth:
                return
            
            if current == target:
                paths.append(path.copy())
                return
            
            for edge in self.edges:
                if edge["from"] == current and edge["to"] not in path:
                    path.append(edge["to"])
                    dfs(edge["to"], target, path, depth + 1)
                    path.pop()
        
        dfs(start, end, [start], 0)
        
        return paths
    
    def detect_cycles(self) -> List[List[str]]:
        """Обнаружить циклы"""
        
        cycles = []
        visited = set()
        
        def dfs(node: str, path: List[str]):
            if node in path:
                # Найден цикл
                cycle_start = path.index(node)
                cycle = path[cycle_start:] + [node]
                cycles.append(cycle)
                return
            
            if node in visited:
                return
            
            visited.add(node)
            path.append(node)
            
            for edge in self.edges:
                if edge["from"] == node:
                    dfs(edge["to"], path.copy())
        
        for node in self.nodes:
            dfs(node, [])
        
        return cycles
    
    def get_statistics(self) -> Dict[str, Any]:
        """Получить статистику графа"""
        
        return {
            "nodes_count": len(self.nodes),
            "edges_count": len(self.edges),
            "total_volume": sum(edge["value"] for edge in self.edges),
            "avg_degree": sum(
                node["in_degree"] + node["out_degree"]
                for node in self.nodes.values()
            ) / len(self.nodes) if self.nodes else 0,
            "max_in_degree": max(
                (node["in_degree"] for node in self.nodes.values()),
                default=0
            ),
            "max_out_degree": max(
                (node["out_degree"] for node in self.nodes.values()),
                default=0
            ),
        }


class TransactionVisualizer:
    """Визуализатор транзакций"""
    
    def __init__(self):
        self.graph = TransactionGraph()
    
    async def build_graph_from_address(
        self,
        address: str,
        chain: str,
        depth: int,
        session: aiohttp.ClientSession,
        timeout: int = 10
    ) -> TransactionGraph:
        """Построить граф транзакций от адреса"""
        
        self.graph = TransactionGraph()
        
        # Получаем транзакции
        transactions = await self._get_transactions(
            address,
            chain,
            session,
            timeout
        )
        
        # Строим граф
        for tx in transactions:
            from_addr = tx.get("from", "")
            to_addr = tx.get("to", "")
            value = tx.get("value", 0)
            tx_hash = tx.get("hash", "")
            
            if from_addr and to_addr:
                self.graph.add_edge(from_addr, to_addr, value, tx_hash)
        
        # Расширяем граф на заданную глубину
        if depth > 1:
            await self._expand_graph(address, chain, depth - 1, session, timeout)
        
        return self.graph
    
    async def _get_transactions(
        self,
        address: str,
        chain: str,
        session: aiohttp.ClientSession,
        timeout: int,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Получить транзакции адреса"""
        
        transactions = []
        
        # Здесь должна быть реальная логика получения транзакций
        # Для примера используем mock данные
        
        return transactions
    
    async def _expand_graph(
        self,
        center: str,
        chain: str,
        depth: int,
        session: aiohttp.ClientSession,
        timeout: int
    ):
        """Расширить граф"""
        
        if depth <= 0:
            return
        
        # Получаем соседей
        neighbors = self.graph.get_neighbors(center)
        
        # Для каждого соседа получаем транзакции
        for neighbor in neighbors:
            transactions = await self._get_transactions(
                neighbor,
                chain,
                session,
                timeout,
                limit=50
            )
            
            for tx in transactions:
                from_addr = tx.get("from", "")
                to_addr = tx.get("to", "")
                value = tx.get("value", 0)
                tx_hash = tx.get("hash", "")
                
                if from_addr and to_addr:
                    self.graph.add_edge(from_addr, to_addr, value, tx_hash)
            
            # Рекурсивно расширяем
            await self._expand_graph(neighbor, chain, depth - 1, session, timeout)
    
    def visualize_ascii(
        self,
        center: Optional[str] = None,
        max_nodes: int = 20
    ) -> str:
        """Визуализировать граф в ASCII"""
        
        if center:
            # Показываем подграф вокруг центра
            subgraph = self.graph.get_subgraph(center, depth=2)
        else:
            subgraph = self.graph
        
        lines = []
        
        lines.append("📊 TRANSACTION GRAPH")
        lines.append("=" * 50)
        
        # Статистика
        stats = subgraph.get_statistics()
        lines.append(f"Nodes: {stats['nodes_count']}")
        lines.append(f"Edges: {stats['edges_count']}")
        lines.append(f"Total Volume: {stats['total_volume']:.6f}")
        lines.append("")
        
        # Топ узлы по активности
        sorted_nodes = sorted(
            subgraph.nodes.items(),
            key=lambda x: x[1]["in_degree"] + x[1]["out_degree"],
            reverse=True
        )
        
        lines.append("🔝 TOP NODES:")
        for i, (addr, node_data) in enumerate(sorted_nodes[:max_nodes], 1):
            label = node_data["label"]
            in_deg = node_data["in_degree"]
            out_deg = node_data["out_degree"]
            total_in = node_data["total_in"]
            total_out = node_data["total_out"]
            
            lines.append(f"{i}. {label}")
            lines.append(f"   In: {in_deg} txs ({total_in:.6f})")
            lines.append(f"   Out: {out_deg} txs ({total_out:.6f})")
        
        lines.append("")
        
        # Показываем связи
        lines.append("🔗 CONNECTIONS:")
        for edge in subgraph.edges[:20]:
            from_label = subgraph.nodes[edge["from"]]["label"]
            to_label = subgraph.nodes[edge["to"]]["label"]
            value = edge["value"]
            
            lines.append(f"{from_label} → {to_label}: {value:.6f}")
        
        return "\n".join(lines)
    
    def analyze_flow_patterns(self) -> Dict[str, Any]:
        """Анализировать паттерны денежных потоков"""
        
        analysis = {
            "hubs": [],  # Узлы с высокой степенью
            "sources": [],  # Узлы только с исходящими
            "sinks": [],  # Узлы только с входящими
            "cycles": [],  # Циклы
            "clusters": [],  # Кластеры
        }
        
        # Находим хабы (узлы с высокой степенью)
        for addr, node_data in self.graph.nodes.items():
            total_degree = node_data["in_degree"] + node_data["out_degree"]
            if total_degree >= 10:
                analysis["hubs"].append({
                    "address": addr,
                    "label": node_data["label"],
                    "degree": total_degree,
                })
        
        # Находим источники и стоки
        for addr, node_data in self.graph.nodes.items():
            if node_data["out_degree"] > 0 and node_data["in_degree"] == 0:
                analysis["sources"].append(addr)
            elif node_data["in_degree"] > 0 and node_data["out_degree"] == 0:
                analysis["sinks"].append(addr)
        
        # Находим циклы
        analysis["cycles"] = self.graph.detect_cycles()
        
        return analysis
    
    def format_analysis_report(self, analysis: Dict[str, Any]) -> str:
        """Форматировать отчет анализа"""
        
        lines = []
        
        lines.append("🔍 FLOW PATTERN ANALYSIS")
        lines.append("=" * 50)
        
        # Хабы
        hubs = analysis.get("hubs", [])
        if hubs:
            lines.append("\n🌐 HUBS (High Activity Nodes):")
            for hub in sorted(hubs, key=lambda x: x["degree"], reverse=True)[:10]:
                lines.append(f"  • {hub['label']}: {hub['degree']} connections")
        
        # Источники
        sources = analysis.get("sources", [])
        if sources:
            lines.append(f"\n📤 SOURCES (Only Outgoing): {len(sources)}")
            for source in sources[:5]:
                node = self.graph.nodes.get(source, {})
                lines.append(f"  • {node.get('label', source)}")
        
        # Стоки
        sinks = analysis.get("sinks", [])
        if sinks:
            lines.append(f"\n📥 SINKS (Only Incoming): {len(sinks)}")
            for sink in sinks[:5]:
                node = self.graph.nodes.get(sink, {})
                lines.append(f"  • {node.get('label', sink)}")
        
        # Циклы
        cycles = analysis.get("cycles", [])
        if cycles:
            lines.append(f"\n🔄 CYCLES DETECTED: {len(cycles)}")
            for i, cycle in enumerate(cycles[:5], 1):
                cycle_labels = [
                    self.graph.nodes.get(addr, {}).get("label", addr)
                    for addr in cycle
                ]
                lines.append(f"  {i}. {' → '.join(cycle_labels)}")
        
        return "\n".join(lines)


class MoneyFlowAnalyzer:
    """Анализатор денежных потоков"""
    
    def __init__(self):
        pass
    
    async def analyze_money_flow(
        self,
        address: str,
        chain: str,
        period_days: int,
        session: aiohttp.ClientSession
    ) -> Dict[str, Any]:
        """
        Анализировать денежные потоки
        
        Returns:
            {
                "total_in": float,
                "total_out": float,
                "net_flow": float,
                "unique_senders": int,
                "unique_receivers": int,
                "top_senders": [...],
                "top_receivers": [...],
                "flow_by_day": [...]
            }
        """
        
        analysis = {
            "total_in": 0.0,
            "total_out": 0.0,
            "net_flow": 0.0,
            "unique_senders": 0,
            "unique_receivers": 0,
            "top_senders": [],
            "top_receivers": [],
            "flow_by_day": [],
        }
        
        # Здесь должна быть реальная логика
        
        return analysis
    
    def detect_suspicious_patterns(
        self,
        graph: TransactionGraph
    ) -> List[Dict[str, Any]]:
        """Обнаружить подозрительные паттерны"""
        
        suspicious = []
        
        # 1. Быстрые циклы (возможная отмывка)
        cycles = graph.detect_cycles()
        for cycle in cycles:
            if len(cycle) <= 5:  # Короткие циклы подозрительны
                suspicious.append({
                    "type": "short_cycle",
                    "severity": "high",
                    "description": f"Short cycle detected: {len(cycle)} nodes",
                    "nodes": cycle,
                })
        
        # 2. Узлы с очень высокой активностью
        for addr, node_data in graph.nodes.items():
            total_degree = node_data["in_degree"] + node_data["out_degree"]
            if total_degree > 100:
                suspicious.append({
                    "type": "high_activity",
                    "severity": "medium",
                    "description": f"Very high activity: {total_degree} transactions",
                    "address": addr,
                })
        
        # 3. Большие суммы в одной транзакции
        for edge in graph.edges:
            if edge["value"] > 100:  # > 100 ETH
                suspicious.append({
                    "type": "large_transfer",
                    "severity": "medium",
                    "description": f"Large transfer: {edge['value']:.2f}",
                    "from": edge["from"],
                    "to": edge["to"],
                    "tx_hash": edge["tx_hash"],
                })
        
        return suspicious
    
    def format_suspicious_report(
        self,
        suspicious: List[Dict[str, Any]]
    ) -> str:
        """Форматировать отчет о подозрительных паттернах"""
        
        if not suspicious:
            return "✅ No suspicious patterns detected"
        
        lines = []
        
        lines.append("⚠️ SUSPICIOUS PATTERNS DETECTED")
        lines.append("=" * 50)
        
        # Группируем по типу
        by_type = defaultdict(list)
        for item in suspicious:
            by_type[item["type"]].append(item)
        
        for pattern_type, items in by_type.items():
            lines.append(f"\n🚨 {pattern_type.upper().replace('_', ' ')} ({len(items)}):")
            
            for item in items[:5]:
                severity = item["severity"]
                desc = item["description"]
                
                severity_icon = "🔴" if severity == "high" else "🟡"
                lines.append(f"  {severity_icon} {desc}")
        
        return "\n".join(lines)
