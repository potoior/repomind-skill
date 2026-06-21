import re
from typing import List, Tuple, Dict, Set
from .models import Document, Entity, Relation, EntityType, RelationType


class KnowledgeExtractor:
    def __init__(self):
        self.technologies: Dict[str, EntityType] = {
            # Frameworks
            "python": EntityType.FRAMEWORK,
            "javascript": EntityType.FRAMEWORK,
            "typescript": EntityType.FRAMEWORK,
            "react": EntityType.FRAMEWORK,
            "vue": EntityType.FRAMEWORK,
            "angular": EntityType.FRAMEWORK,
            "nodejs": EntityType.FRAMEWORK,
            "node.js": EntityType.FRAMEWORK,
            "fastapi": EntityType.FRAMEWORK,
            "flask": EntityType.FRAMEWORK,
            "django": EntityType.FRAMEWORK,
            "express": EntityType.FRAMEWORK,
            "spring": EntityType.FRAMEWORK,
            "pandas": EntityType.FRAMEWORK,
            "spark": EntityType.FRAMEWORK,
            # Databases
            "postgres": EntityType.DATABASE,
            "postgresql": EntityType.DATABASE,
            "mysql": EntityType.DATABASE,
            "redis": EntityType.DATABASE,
            "mongodb": EntityType.DATABASE,
            "sqlite": EntityType.DATABASE,
            "elasticsearch": EntityType.DATABASE,
            # Tools
            "docker": EntityType.TOOL,
            "kubernetes": EntityType.TOOL,
            "k8s": EntityType.TOOL,
            "kafka": EntityType.TOOL,
            "nginx": EntityType.TOOL,
            "terraform": EntityType.TOOL,
            # Protocols
            "http": EntityType.PROTOCOL,
            "https": EntityType.PROTOCOL,
            "grpc": EntityType.PROTOCOL,
            "websocket": EntityType.PROTOCOL,
            "rest": EntityType.PROTOCOL,
            "restful": EntityType.PROTOCOL,
        }

        self.non_module_headings = {
            "项目概述", "项目简介", "概述", "简介", "介绍",
            "核心模块", "主要功能", "功能特性", "特性",
            "技术栈", "技术架构", "架构", "架构设计",
            "快速开始", "快速入门", "开始使用", "上手",
            "安装指南", "安装", "部署", "安装方式", "安装步骤",
            "文档", "参考资料", "链接", "文档列表",
            "贡献指南", "参与贡献", "贡献",
            "许可证", "license", "许可",
            "更新日志", "changelog",
            "目录", "table of contents",
            "系统架构", "系统要求",
            "核心组件", "组件",
            "数据流", "处理模式", "容错机制",
            "扩展性", "水平扩展", "垂直扩展",
            "配置管理", "配置", "配置说明", "配置文件",
            "快速开始", "5分钟上手",
            "第一步", "第二步", "第三步", "第四步", "第五步", "第六步",
            "下一步", "查看结果", "验证安装",
            "故障排除", "常见问题", "升级",
            "依赖安装", "可选依赖", "核心依赖", "完整依赖",
            "示例", "例子", "基础端点", "内置", "自定义",
        }

    def extract_from_documents(self, documents: List[Document], code_files: List[Tuple[str, str]] = None) -> Tuple[List[Entity], List[Relation]]:
        all_entities = []
        all_relations = []

        for doc in documents:
            entities, relations = self._extract_from_document(doc)
            all_entities.extend(entities)
            all_relations.extend(relations)

        if code_files:
            for file_path, content in code_files:
                entities, relations = self._extract_from_code(file_path, content)
                all_entities.extend(entities)
                all_relations.extend(relations)

        all_entities = self._deduplicate_entities(all_entities)
        all_relations = self._deduplicate_relations(all_relations)
        all_relations = self._infer_relations(all_entities, all_relations)

        return all_entities, all_relations

    def _extract_from_document(self, doc: Document) -> Tuple[List[Entity], List[Relation]]:
        entities = []
        relations = []

        doc_entity = Entity(
            name=doc.title,
            type=EntityType.DOCUMENT,
            description=f"文档: {doc.path}",
            source_file=doc.path
        )
        entities.append(doc_entity)

        content_lower = doc.content.lower()
        mentioned_techs: Set[str] = set()

        for tech, entity_type in self.technologies.items():
            if tech in content_lower:
                mentioned_techs.add(tech)
                entities.append(Entity(
                    name=tech,
                    type=entity_type,
                    source_file=doc.path
                ))

        for tech in mentioned_techs:
            relations.append(Relation(
                source=doc.title,
                target=tech,
                type=RelationType.USES,
                source_file=doc.path
            ))

        api_endpoints = self._extract_api_endpoints(doc.content)
        for endpoint in api_endpoints:
            entities.append(Entity(
                name=endpoint["path"],
                type=EntityType.API,
                description=f"{endpoint['method']} {endpoint['path']} - {endpoint.get('description', '')}",
                source_file=doc.path
            ))
            relations.append(Relation(
                source=doc.title,
                target=endpoint["path"],
                type=RelationType.CONTAINS,
                source_file=doc.path
            ))

        commands = self._extract_commands(doc.content)
        for cmd in commands:
            entities.append(Entity(
                name=cmd["name"],
                type=EntityType.COMMAND,
                description=cmd.get("description", ""),
                source_file=doc.path
            ))

        for heading in doc.headings:
            if heading.startswith("## "):
                heading_name = heading[3:].strip()
                if len(heading_name) > 2 and not self._is_non_module_heading(heading_name):
                    description = self._extract_heading_description(doc.content, heading)
                    entities.append(Entity(
                        name=heading_name,
                        type=EntityType.MODULE,
                        description=description,
                        source_file=doc.path
                    ))
                    relations.append(Relation(
                        source=doc.title,
                        target=heading_name,
                        type=RelationType.CONTAINS,
                        source_file=doc.path
                    ))

        modules = self._extract_listed_modules(doc.content)
        for module in modules:
            entities.append(Entity(
                name=module,
                type=EntityType.MODULE,
                source_file=doc.path
            ))
            relations.append(Relation(
                source=doc.title,
                target=module,
                type=RelationType.DOCUMENTS,
                source_file=doc.path
            ))

        return entities, relations

    def _extract_from_code(self, file_path: str, content: str) -> Tuple[List[Entity], List[Relation]]:
        entities = []
        relations = []

        file_name = file_path.split('/')[-1].split('\\')[-1].replace('.py', '')

        docstring_match = re.search(r'"""(.*?)"""', content, re.DOTALL)
        module_desc = docstring_match.group(1).strip().split('\n')[0] if docstring_match else None

        entities.append(Entity(
            name=file_name,
            type=EntityType.MODULE,
            description=module_desc or f"模块: {file_path}",
            source_file=file_path
        ))

        classes = re.finditer(r'class\s+(\w+)\s*(?:\(([^)]*)\))?:\s*\n\s*(?:"""(.*?)""")?', content, re.DOTALL)
        for match in classes:
            class_name = match.group(1)
            parent_class = match.group(2)
            docstring = match.group(3)
            
            desc = docstring.strip().split('\n')[0] if docstring else f"类: {class_name}"
            entities.append(Entity(
                name=class_name,
                type=EntityType.MODULE,
                description=desc,
                source_file=file_path
            ))
            
            relations.append(Relation(
                source=file_name,
                target=class_name,
                type=RelationType.CONTAINS,
                source_file=file_path
            ))
            
            if parent_class and parent_class.strip() not in ['ABC', 'object', 'BaseModel']:
                relations.append(Relation(
                    source=class_name,
                    target=parent_class.strip(),
                    type=RelationType.EXTENDS,
                    source_file=file_path
                ))

        functions = re.finditer(r'def\s+(\w+)\s*\([^)]*\)\s*(?:->[^:]+)?:\s*\n\s*(?:"""(.*?)""")?', content, re.DOTALL)
        for match in functions:
            func_name = match.group(1)
            docstring = match.group(2)
            
            if func_name.startswith('_'):
                continue
                
            desc = docstring.strip().split('\n')[0] if docstring else None
            entities.append(Entity(
                name=func_name,
                type=EntityType.FEATURE,
                description=desc,
                source_file=file_path
            ))

        imports = re.findall(r'(?:from|import)\s+([\w.]+)', content)
        skip_modules = {'os', 'sys', 're', 'json', 'typing', 'abc', 'dataclasses', 'csv', 'psycopg2', 'kafka'}
        for imp in imports:
            parts = imp.split('.')
            if len(parts) > 0:
                module_name = parts[0]
                if module_name not in skip_modules and not module_name.startswith('__'):
                    relations.append(Relation(
                        source=file_name,
                        target=module_name,
                        type=RelationType.DEPENDS_ON,
                        source_file=file_path
                    ))

        return entities, relations

    def _extract_api_endpoints(self, content: str) -> List[Dict]:
        endpoints = []
        
        patterns = [
            r'[-*]\s+`(GET|POST|PUT|DELETE|PATCH)\s+([^`]+)`\s*[-–—]?\s*(.*)',
            r'[-*]\s+\*\*(GET|POST|PUT|DELETE|PATCH)\s+([^*]+)\*\*\s*[-–—]?\s*(.*)',
            r'`(GET|POST|PUT|DELETE|PATCH)\s+(/[^`]+)`',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            for match in matches:
                method = match[0].upper()
                path = match[1].strip()
                desc = match[2].strip() if len(match) > 2 else ""
                endpoints.append({
                    "method": method,
                    "path": path,
                    "description": desc
                })
        
        return endpoints

    def _extract_commands(self, content: str) -> List[Dict]:
        commands = []
        
        patterns = [
            r'```bash\n((?:[^\n]*\n)*?)```',
            r'```\n((?:[^\n]*\n)*?)```',
        ]
        
        for pattern in patterns:
            blocks = re.findall(pattern, content, re.DOTALL)
            for block in blocks:
                lines = block.strip().split('\n')
                for line in lines:
                    line = line.strip()
                    if line.startswith('dataflow ') or line.startswith('taskflow '):
                        parts = line.split()
                        if len(parts) >= 2:
                            cmd_name = ' '.join(parts[:2])
                            commands.append({
                                "name": cmd_name,
                                "description": f"命令: {line}"
                            })
        
        return commands

    def _extract_heading_description(self, content: str, heading: str) -> str:
        pattern = f"{re.escape(heading)}\n(.*?)(?:\n#|\Z)"
        match = re.search(pattern, content, re.DOTALL)
        if match:
            desc_lines = match.group(1).strip().split('\n')
            for line in desc_lines:
                line = line.strip()
                if line and not line.startswith('#') and not line.startswith('```'):
                    return line[:100]
        return None

    def _is_non_module_heading(self, heading: str) -> bool:
        heading_lower = heading.lower()
        for non_module in self.non_module_headings:
            if non_module in heading_lower:
                return True
        return False

    def _extract_listed_modules(self, content: str) -> List[str]:
        modules = []
        patterns = [
            r'[-*]\s+\*\*(\w+)\*\*\s*[-–—]',
            r'[-*]\s+\*\*(\w+)\*\*',
            r'`(\w+)`\s*[-–—]',
        ]

        for pattern in patterns:
            matches = re.findall(pattern, content)
            for match in matches:
                if len(match) > 2 and not self._is_non_module_heading(match):
                    modules.append(match)

        return modules

    def _deduplicate_entities(self, entities: List[Entity]) -> List[Entity]:
        seen = set()
        unique_entities = []

        for entity in entities:
            key = (entity.name.lower(), entity.type)
            if key not in seen:
                seen.add(key)
                unique_entities.append(entity)

        return unique_entities

    def _deduplicate_relations(self, relations: List[Relation]) -> List[Relation]:
        seen = set()
        unique_relations = []

        for relation in relations:
            key = (relation.source.lower(), relation.target.lower(), relation.type)
            if key not in seen:
                seen.add(key)
                unique_relations.append(relation)

        return unique_relations

    def _infer_relations(self, entities: List[Entity], relations: List[Relation]) -> List[Relation]:
        new_relations = []

        for entity in entities:
            if entity.type == EntityType.DATABASE:
                for other in entities:
                    if other.type == EntityType.FRAMEWORK:
                        existing = any(
                            r.source.lower() == other.name.lower() and r.target.lower() == entity.name.lower()
                            for r in relations + new_relations
                        )
                        if not existing:
                            new_relations.append(Relation(
                                source=other.name,
                                target=entity.name,
                                type=RelationType.USES,
                                source_file="inferred"
                            ))

        return relations + new_relations