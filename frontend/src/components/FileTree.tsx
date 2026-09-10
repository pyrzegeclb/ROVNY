import { File, Folder, ChevronDown, ChevronRight } from 'lucide-react';
import { useState } from 'react';
import type { FileItem } from '../types';
type Node = { children: Record<string, Node>; path?: string };
function Branch({ name, node, active, selected, onOpen, onSelect }: { name: string; node: Node; active?: string; selected: string[]; onOpen: (p: string) => void; onSelect: (p: string) => void }) {
  const [expanded, setExpanded] = useState(true);
  if (node.path) return <div className={'tree-file ' + (active === node.path ? 'active' : '')}><input aria-label={'Include ' + node.path + ' in AI context'} type="checkbox" checked={selected.includes(node.path)} onChange={() => onSelect(node.path!)}/><button onClick={() => onOpen(node.path!)} title={node.path}><File size={14}/><span>{name}</span></button></div>;
  return <div><button className="tree-folder" onClick={() => setExpanded(!expanded)}>{expanded ? <ChevronDown size={12}/> : <ChevronRight size={12}/>}<Folder size={14}/>{name}</button>{expanded && <div className="tree-children">{Object.entries(node.children).map(([n, child]) => <Branch key={n} name={n} node={child} active={active} selected={selected} onOpen={onOpen} onSelect={onSelect}/>)}</div>}</div>;
}
export function FileTree({ files, ...props }: { files: FileItem[]; active?: string; selected: string[]; onOpen: (p: string) => void; onSelect: (p: string) => void }) {
  const root: Node = { children: {} };
  for (const file of files) { let node = root; for (const part of file.path.split('/')) node = node.children[part] ||= { children: {} }; node.path = file.path; }
  return <div className="tree">{Object.entries(root.children).map(([name, node]) => <Branch key={name} name={name} node={node} {...props}/>)}</div>;
}
