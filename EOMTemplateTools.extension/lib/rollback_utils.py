 # -*- coding: utf-8 -*-
 """Rollback utilities for undoing AUTO_EOM placements.
 
 This module provides functions for finding and deleting elements
 that were automatically placed by EOM Template Tools.
 
 Elements are identified by their Comments parameter containing
 the AUTO_EOM tag prefix.
 
 Example:
     >>> from rollback_utils import find_tagged_elements, delete_elements
     >>> elements = find_tagged_elements(doc, "AUTO_EOM:SOCKET")
     >>> count = delete_elements(doc, elements)
     >>> print(f"Deleted {count} elements")
 """
 from __future__ import print_function
 
 import re
 from datetime import datetime
 from typing import Dict, List, Optional, Set, Tuple
 
 try:
     from pyrevit import DB, revit
 except ImportError:
     DB = None
     revit = None
 
 
 # Default tag prefix used by all EOM tools
 DEFAULT_TAG_PREFIX = "AUTO_EOM"
 
 # Regex pattern to parse tag format: AUTO_EOM:TOOL:TIMESTAMP
 TAG_PATTERN = re.compile(
     r"^(AUTO_EOM)(?::([A-Z_]+))?(?::(\d{8}_\d{6}))?",
     re.IGNORECASE
 )
 
 
 def parse_tag(comment: Optional[str]) -> Optional[Dict[str, str]]:
     """Parse AUTO_EOM tag from element comment.
     
     Args:
         comment: The Comments parameter value from an element.
         
     Returns:
         Dictionary with 'prefix', 'tool', 'timestamp' keys if valid tag,
         None if not a valid AUTO_EOM tag.
         
     Examples:
         >>> parse_tag("AUTO_EOM:SOCKET:20260117_143022")
         {'prefix': 'AUTO_EOM', 'tool': 'SOCKET', 'timestamp': '20260117_143022'}
         >>> parse_tag("AUTO_EOM:LIGHT")
         {'prefix': 'AUTO_EOM', 'tool': 'LIGHT', 'timestamp': None}
         >>> parse_tag("Some other comment")
         None
     """
     if not comment:
         return None
     
     comment = comment.strip()
     match = TAG_PATTERN.match(comment)
     
     if not match:
         # Try simple prefix match for legacy tags
         if comment.upper().startswith(DEFAULT_TAG_PREFIX):
             parts = comment.split(":")
             return {
                 "prefix": parts[0] if parts else DEFAULT_TAG_PREFIX,
                 "tool": parts[1] if len(parts) > 1 else None,
                 "timestamp": parts[2] if len(parts) > 2 else None,
             }
         return None
     
     return {
         "prefix": match.group(1) or DEFAULT_TAG_PREFIX,
         "tool": match.group(2),
         "timestamp": match.group(3),
     }
 
 
 def generate_tag(tool_name: str, include_timestamp: bool = True) -> str:
     """Generate a new AUTO_EOM tag for element comments.
     
     Args:
         tool_name: Name of the tool (e.g., 'SOCKET', 'LIGHT', 'SWITCH').
         include_timestamp: Whether to include timestamp in tag.
         
     Returns:
         Formatted tag string.
         
     Examples:
         >>> generate_tag("SOCKET", include_timestamp=False)
         'AUTO_EOM:SOCKET'
         >>> generate_tag("LIGHT")  # with timestamp
         'AUTO_EOM:LIGHT:20260117_143022'
     """
     tool_name = tool_name.upper().replace(" ", "_")
     
     if include_timestamp:
         timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
         return "{}:{}:{}".format(DEFAULT_TAG_PREFIX, tool_name, timestamp)
     
     return "{}:{}".format(DEFAULT_TAG_PREFIX, tool_name)
 
 
 def find_tagged_elements(
     doc,
     tag_filter: Optional[str] = None,
     tool_filter: Optional[str] = None,
 ) -> List:
     """Find all elements with AUTO_EOM tags in their Comments.
     
     Args:
         doc: Revit document to search.
         tag_filter: Optional full tag to match (e.g., "AUTO_EOM:SOCKET").
         tool_filter: Optional tool name to filter by (e.g., "SOCKET").
         
     Returns:
         List of Revit elements matching the filter.
         
     Examples:
         >>> elements = find_tagged_elements(doc)  # all AUTO_EOM elements
         >>> sockets = find_tagged_elements(doc, tool_filter="SOCKET")
     """
     if doc is None or DB is None:
         return []
     
     elements = []
     
     try:
         # Use parameter filter for efficiency
         provider = DB.ParameterValueProvider(
             DB.ElementId(DB.BuiltInParameter.ALL_MODEL_INSTANCE_COMMENTS)
         )
         
         # Filter for elements containing AUTO_EOM
         rule = DB.FilterStringRule(
             provider,
             DB.FilterStringContains(),
             DEFAULT_TAG_PREFIX
         )
         param_filter = DB.ElementParameterFilter(rule)
         
         collector = (
             DB.FilteredElementCollector(doc)
             .WhereElementIsNotElementType()
             .WherePasses(param_filter)
         )
         
         for elem in collector:
             try:
                 comment_param = elem.get_Parameter(
                     DB.BuiltInParameter.ALL_MODEL_INSTANCE_COMMENTS
                 )
                 if not comment_param:
                     continue
                     
                 comment = comment_param.AsString()
                 if not comment:
                     continue
                 
                 parsed = parse_tag(comment)
                 if not parsed:
                     continue
                 
                 # Apply filters
                 if tag_filter:
                     if not comment.upper().startswith(tag_filter.upper()):
                         continue
                 
                 if tool_filter:
                     if parsed.get("tool", "").upper() != tool_filter.upper():
                         continue
                 
                 elements.append(elem)
                 
             except Exception:
                 continue
                 
     except Exception:
         pass
     
     return elements
 
 
 def get_unique_tags(doc) -> List[Tuple[str, int]]:
     """Get all unique AUTO_EOM tags in the document with counts.
     
     Args:
         doc: Revit document to search.
         
     Returns:
         List of (tag, count) tuples, sorted by count descending.
         
     Examples:
         >>> tags = get_unique_tags(doc)
         >>> for tag, count in tags:
         ...     print(f"{tag}: {count} elements")
         AUTO_EOM:SOCKET: 45 elements
         AUTO_EOM:LIGHT: 23 elements
     """
     if doc is None:
         return []
     
     tag_counts: Dict[str, int] = {}
     elements = find_tagged_elements(doc)
     
     for elem in elements:
         try:
             comment_param = elem.get_Parameter(
                 DB.BuiltInParameter.ALL_MODEL_INSTANCE_COMMENTS
             )
             if not comment_param:
                 continue
                 
             comment = comment_param.AsString()
             parsed = parse_tag(comment)
             
             if parsed:
                 # Create tag key (prefix + tool, without timestamp)
                 tool = parsed.get("tool") or "UNKNOWN"
                 tag_key = "{}:{}".format(parsed["prefix"], tool)
                 tag_counts[tag_key] = tag_counts.get(tag_key, 0) + 1
                 
         except Exception:
             continue
     
     # Sort by count descending
     sorted_tags = sorted(tag_counts.items(), key=lambda x: -x[1])
     return sorted_tags
 
 
 def get_unique_tools(doc) -> List[str]:
     """Get list of unique tool names from AUTO_EOM tags.
     
     Args:
         doc: Revit document to search.
         
     Returns:
         List of unique tool names (e.g., ['SOCKET', 'LIGHT', 'SWITCH']).
     """
     tags = get_unique_tags(doc)
     tools: Set[str] = set()
     
     for tag, _ in tags:
         parts = tag.split(":")
         if len(parts) >= 2:
             tools.add(parts[1])
     
     return sorted(tools)
 
 
 def delete_elements(doc, elements: List, transaction_name: str = "Undo AUTO_EOM") -> int:
     """Delete elements from the document.
     
     Args:
         doc: Revit document.
         elements: List of elements to delete.
         transaction_name: Name for the Revit transaction.
         
     Returns:
         Number of elements successfully deleted.
     """
     if doc is None or not elements or DB is None:
         return 0
     
     deleted = 0
     element_ids = []
     
     for elem in elements:
         try:
             if hasattr(elem, "Id"):
                 element_ids.append(elem.Id)
         except Exception:
             continue
     
     if not element_ids:
         return 0
     
     try:
         # Use transaction context if available
         if revit and hasattr(revit, "Transaction"):
             with revit.Transaction(transaction_name):
                 for eid in element_ids:
                     try:
                         doc.Delete(eid)
                         deleted += 1
                     except Exception:
                         continue
         else:
             # Manual transaction
             t = DB.Transaction(doc, transaction_name)
             t.Start()
             try:
                 for eid in element_ids:
                     try:
                         doc.Delete(eid)
                         deleted += 1
                     except Exception:
                         continue
                 t.Commit()
             except Exception:
                 t.RollBack()
                 return 0
                 
     except Exception:
         return 0
     
     return deleted
 
 
 def delete_by_tool(doc, tool_name: str, transaction_name: Optional[str] = None) -> int:
     """Delete all elements created by a specific tool.
     
     Args:
         doc: Revit document.
         tool_name: Tool name to filter by (e.g., 'SOCKET', 'LIGHT').
         transaction_name: Optional transaction name.
         
     Returns:
         Number of elements deleted.
         
     Examples:
         >>> count = delete_by_tool(doc, "SOCKET")
         >>> print(f"Deleted {count} socket elements")
     """
     elements = find_tagged_elements(doc, tool_filter=tool_name)
     
     if not transaction_name:
         transaction_name = "Undo AUTO_EOM:{}".format(tool_name.upper())
     
     return delete_elements(doc, elements, transaction_name)
 
 
 def delete_all_auto_eom(doc) -> int:
     """Delete ALL elements with AUTO_EOM tags.
     
     WARNING: This is destructive and cannot be undone after save!
     
     Args:
         doc: Revit document.
         
     Returns:
         Number of elements deleted.
     """
     elements = find_tagged_elements(doc)
     return delete_elements(doc, elements, "Delete All AUTO_EOM")
