/** Transforma as specs estruturadas do backend em rótulos legíveis ("i7 13ª geração", "32GB RAM"). */
import { formatGB } from './format.js';

const CATEGORY = {
  notebook: 'Notebook',
  desktop: 'PC',
  tablet: 'Tablet',
  monitor: 'Monitor',
  placa_video: 'Placa de vídeo',
  placa_mae: 'Placa-mãe',
  processador: 'Processador',
  memoria: 'Memória',
  armazenamento: 'SSD/HD',
  fonte: 'Fonte',
  gabinete: 'Gabinete',
};

export function cpuLabel(specs) {
  const line = specs.cpu_line;
  if (!line) return specs.cpu_brand ? specs.cpu_brand.toUpperCase() : '';
  const pretty = line
    .replace(/^ryzen_ai(\d)/, 'Ryzen AI $1')
    .replace(/^ryzen(\d)/, 'Ryzen $1')
    .replace(/^ultra(\d)/, 'Core Ultra $1')
    .replace(/^core(\d)/, 'Core $1')
    .replace(/^m(\d)/, 'Apple M$1');
  let label = pretty;
  if (specs.cpu_model) label += ` ${specs.cpu_model.toUpperCase()}`;
  else if (specs.cpu_generation && /^i\d$/.test(line)) label += ` ${specs.cpu_generation}ª geração`;
  else if (specs.cpu_generation && line.startsWith('ryzen')) label += ` série ${specs.cpu_generation}000`;
  return label;
}

/** Lista de "chips" para mostrar como a busca/anúncio foi entendido. */
export function specChips(specs = {}) {
  const chips = [];
  if (specs.category) chips.push(CATEGORY[specs.category] || specs.category);
  if (specs.brand) chips.push(specs.brand[0].toUpperCase() + specs.brand.slice(1));
  const cpu = cpuLabel(specs);
  if (cpu) chips.push(cpu);
  if (specs.ram_gb) chips.push(`${formatGB(specs.ram_gb)} RAM`);
  if (specs.storage_gb) chips.push(`${formatGB(specs.storage_gb)}${specs.storage_type ? ` ${specs.storage_type.toUpperCase()}` : ''}`);
  if (specs.gpu) chips.push(specs.gpu.toUpperCase());
  if (specs.screen_in) chips.push(`${specs.screen_in}"`);
  (specs.keywords || []).forEach((k) => chips.push(`"${k}"`));
  return chips;
}
