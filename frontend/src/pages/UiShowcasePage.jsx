import { useState } from 'react';
import styles from './UiShowcasePage.module.css';
import Button from '../components/ui/Button/Button.jsx';
import Input from '../components/ui/Input/Input.jsx';
import SearchBar from '../components/ui/SearchBar/SearchBar.jsx';
import Select from '../components/ui/Select/Select.jsx';
import Checkbox from '../components/ui/Checkbox/Checkbox.jsx';
import Card from '../components/ui/Card/Card.jsx';
import Badge from '../components/ui/Badge/Badge.jsx';
import Spinner from '../components/ui/Spinner/Spinner.jsx';
import Skeleton from '../components/ui/Skeleton/Skeleton.jsx';
import EmptyState from '../components/ui/EmptyState/EmptyState.jsx';
import ErrorMessage from '../components/ui/ErrorMessage/ErrorMessage.jsx';
import Modal from '../components/ui/Modal/Modal.jsx';
import Tooltip from '../components/ui/Tooltip/Tooltip.jsx';
import { Toast, useToast } from '../components/ui/Toast/Toast.jsx';
import PriceTag from '../components/ui/PriceTag/PriceTag.jsx';
import StoreTag from '../components/ui/StoreTag/StoreTag.jsx';
import Icon, { ICON_NAMES } from '../components/ui/Icon/Icon.jsx';
import OfferCard from '../components/features/OfferCard/OfferCard.jsx';
import StoreStatusBar from '../components/features/StoreStatusBar/StoreStatusBar.jsx';

const COLORS = [
  'bg', 'surface', 'surface-muted', 'border', 'text', 'text-muted', 'text-subtle',
  'accent', 'accent-hover', 'accent-soft', 'deal', 'deal-soft', 'success', 'success-soft',
  'error', 'error-soft', 'warning', 'warning-soft',
];
const SPACES = [1, 2, 3, 4, 5, 6, 7, 8, 9];
const RADII = ['sm', 'md', 'lg', 'pill'];
const SHADOWS = ['sm', 'md', 'lg'];
const FONT_SIZES = ['xs', 'sm', 'md', 'lg', 'xl', '2xl', '3xl'];

const SAMPLE_OFFER = {
  store: 'kabum', store_name: 'KaBuM!', external_id: 'demo1',
  title: 'Notebook Dell Inspiron 15, Intel Core i7-13620H 13ª Geração, 32GB RAM, SSD 1TB, Tela 15.6" Full HD',
  url: '#', image_url: null, price_cash: 4899.9, price_installment: 5444.33, installments: 10, installment_value: 544.43,
  price_list: 6499, discount_pct: 24.6, shipping: 0, seller: 'KaBuM!', is_official: true, condition: 'novo',
  specs: { brand: 'dell', cpu_line: 'i7', cpu_model: '13620h', cpu_generation: 13, ram_gb: 32, storage_gb: 1024, storage_type: 'ssd', screen_in: 15.6 },
  match_score: 100, match_level: 'exato', match_reasons: [], collected_at: new Date().toISOString(), history: null,
};
const SAMPLE_OFFER_2 = {
  ...SAMPLE_OFFER, external_id: 'demo2', store: 'mercadolivre', store_name: 'Mercado Livre',
  title: 'Notebook Lenovo Ideapad Slim 3 Core I7 13ª Geração Ssd 512gb', price_cash: 4599, price_list: null,
  discount_pct: null, shipping: null, seller: 'LOJA_TECH_BR', seller_reputation: 'MercadoLíder Gold', is_official: false,
  specs: { brand: 'lenovo', cpu_line: 'i7', cpu_generation: 13, storage_gb: 512 }, match_score: 83,
  match_level: 'provavel', match_reasons: ['RAM não informada no título'], history: { verdict: 'suspeito' },
};

function Section({ title, children }) {
  return (
    <section className={styles.section}>
      <h2 className={styles.sectionTitle}>{title}</h2>
      {children}
    </section>
  );
}

/** Página interna (só em desenvolvimento) com todos os componentes base e tokens. Abra com #ui na URL. */
export default function UiShowcasePage() {
  const [text, setText] = useState('notebook 32gb ram i7 13th');
  const [checked, setChecked] = useState(true);
  const [sort, setSort] = useState('price');
  const [modal, setModal] = useState(false);
  const toast = useToast();

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <h1 className={styles.title}>Padrão visual</h1>
        <p className={styles.subtitle}>Todos os componentes base e tokens. Use esta página para conferir mudanças no design system.</p>
      </header>

      <Section title="Cores">
        <div className={styles.swatches}>
          {COLORS.map((c) => (
            <div key={c} className={styles.swatch}>
              <span className={styles.swatchColor} data-color={c} />
              <code className={styles.code}>--color-{c}</code>
            </div>
          ))}
        </div>
      </Section>

      <Section title="Tipografia">
        <div className={styles.stack}>
          {FONT_SIZES.map((s) => (
            <p key={s} className={styles.fontSample} data-size={s}>
              <code className={styles.code}>--font-size-{s}</code> Notebook i7 13ª geração 32GB
            </p>
          ))}
        </div>
      </Section>

      <Section title="Espaçamentos, raios e sombras">
        <div className={styles.row}>
          {SPACES.map((s) => (
            <div key={s} className={styles.spaceItem}>
              <span className={styles.spaceBar} data-space={s} />
              <code className={styles.code}>{s}</code>
            </div>
          ))}
        </div>
        <div className={styles.row}>
          {RADII.map((r) => (
            <div key={r} className={styles.radiusBox} data-radius={r}>
              <code className={styles.code}>{r}</code>
            </div>
          ))}
          {SHADOWS.map((s) => (
            <div key={s} className={styles.shadowBox} data-shadow={s}>
              <code className={styles.code}>shadow-{s}</code>
            </div>
          ))}
        </div>
      </Section>

      <Section title="Button">
        <div className={styles.row}>
          <Button>Primary</Button>
          <Button variant="secondary">Secondary</Button>
          <Button variant="ghost">Ghost</Button>
          <Button icon="search">Com ícone</Button>
          <Button variant="secondary" iconRight="external-link">Ver na loja</Button>
          <Button variant="secondary" icon="refresh" aria-label="Só ícone" />
        </div>
        <div className={styles.row}>
          <Button size="sm">Pequeno</Button>
          <Button size="md">Médio</Button>
          <Button size="lg">Grande</Button>
          <Button loading>Carregando</Button>
          <Button variant="secondary" loading>Carregando</Button>
          <Button disabled>Desabilitado</Button>
        </div>
      </Section>

      <Section title="Input, SearchBar, Select, Checkbox">
        <div className={styles.grid2}>
          <Input label="Nome" placeholder="Digite algo" hint="Texto de ajuda" />
          <Input label="Preço máximo" prefix="R$" placeholder="5000" icon="tag" />
          <Input label="Com erro" defaultValue="abc" error="Use só números" />
          <Select label="Ordenar por" options={[{ value: 'price', label: 'Menor preço' }, { value: 'discount', label: 'Maior desconto' }]} value={sort} onChange={setSort} />
        </div>
        <SearchBar value={text} onChange={setText} onSubmit={(v) => toast.show(`Buscar: ${v}`)} />
        <div className={styles.row}>
          <Checkbox label="Só lojas oficiais" checked={checked} onChange={setChecked} />
          <Checkbox label="Com descrição" description="Texto menor explicando a opção" checked={!checked} onChange={(v) => setChecked(!v)} />
          <Checkbox label="Desabilitado" checked={false} onChange={() => {}} disabled />
        </div>
      </Section>

      <Section title="Badge">
        <div className={styles.row}>
          <Badge tone="accent" variant="solid" icon="sparkle">Melhor oferta</Badge>
          <Badge tone="deal" variant="solid">-25%</Badge>
          <Badge tone="deal">-8%</Badge>
          <Badge tone="success" icon="shield">Loja oficial</Badge>
          <Badge icon="truck">Frete grátis</Badge>
          <Badge tone="warning">Recondicionado</Badge>
          <Badge tone="error">Indisponível</Badge>
          <Badge tone="accent">32GB RAM</Badge>
          <Badge tone="deal" icon="trending-down" size="sm">Promoção de verdade</Badge>
        </div>
      </Section>

      <Section title="PriceTag e StoreTag">
        <div className={styles.row}>
          <Card><PriceTag cash={4899.9} listPrice={6499} installmentTotal={5444.33} installments={10} installmentValue={544.43} /></Card>
          <Card><PriceTag cash={3999} installmentTotal={3999} installments={10} installmentValue={399.9} highlight size="lg" /></Card>
          <Card><PriceTag cash={null} installmentTotal={2599} installments={12} installmentValue={216.58} /></Card>
        </div>
        <div className={styles.row}>
          {['kabum', 'mercadolivre', 'amazon', 'shopee', 'pichau', 'fastshop', 'terabyte', 'nova-loja'].map((s) => (
            <StoreTag key={s} store={s} name={s === 'nova-loja' ? 'Nova Loja' : undefined} />
          ))}
        </div>
      </Section>

      <Section title="Card">
        <div className={styles.grid3}>
          <Card>Card padrão</Card>
          <Card interactive>Card interativo (passe o mouse)</Card>
          <Card highlighted>Card em destaque</Card>
        </div>
      </Section>

      <Section title="Spinner, Skeleton, Tooltip">
        <div className={styles.row}>
          <Spinner size="sm" />
          <Spinner />
          <Spinner size="lg" />
          <Tooltip content="RAM não informada no título">
            <Button variant="secondary" size="sm" icon="info">Passe o mouse</Button>
          </Tooltip>
        </div>
        <Card className={styles.skeletonDemo}>
          <Skeleton shape="title" width="1/2" />
          <Skeleton shape="text" lines={3} />
          <Skeleton shape="block" width="1/3" />
        </Card>
      </Section>

      <Section title="EmptyState e ErrorMessage">
        <div className={styles.grid2}>
          <Card><EmptyState emoji="😕" title="Não achamos ofertas para isso" description="Tente tirar algum filtro." /></Card>
          <Card><EmptyState icon="bell" title="Nenhum produto monitorado" description="Monitore um produto para ser avisado quando o preço cair." action={<Button size="sm">Monitorar</Button>} /></Card>
        </div>
        <ErrorMessage onRetry={() => toast.show('Tentando de novo…')}>Não consegui falar com o servidor.</ErrorMessage>
        <ErrorMessage tone="warning" title="Amazon indisponível no momento" compact />
      </Section>

      <Section title="Modal e Toast">
        <div className={styles.row}>
          <Button variant="secondary" onClick={() => setModal(true)}>Abrir modal</Button>
          <Button variant="secondary" onClick={() => toast.show('Busca salva!', { tone: 'success' })}>Toast sucesso</Button>
          <Button variant="secondary" onClick={() => toast.show('Loja X indisponível no momento', { tone: 'error' })}>Toast erro</Button>
        </div>
        <div className={styles.stack}>
          <Toast message="Toast informativo" />
          <Toast tone="success" message="Preço caiu! Agora R$ 4.599,00" />
          <Toast tone="warning" message="Mercado Livre precisa de chave de API" />
        </div>
        <Modal open={modal} onClose={() => setModal(false)} title="Exemplo de modal" footer={<><Button variant="ghost" onClick={() => setModal(false)}>Cancelar</Button><Button onClick={() => setModal(false)}>Confirmar</Button></>}>
          <p>Fecha com Esc, clique fora ou no X.</p>
        </Modal>
      </Section>

      <Section title="Icon">
        <div className={styles.icons}>
          {ICON_NAMES.map((n) => (
            <div key={n} className={styles.iconItem}>
              <Icon name={n} size="lg" />
              <code className={styles.code}>{n}</code>
            </div>
          ))}
        </div>
      </Section>

      <Section title="Componentes de funcionalidade">
        <StoreStatusBar
          stores={{
            kabum: { name: 'KaBuM!', status: 'ok', offerCount: 5, elapsed_ms: 3700, total_found: 91, excluded_count: 85 },
            mercadolivre: { name: 'Mercado Livre', status: 'not_configured', message: 'Configure ML_CLIENT_ID e ML_CLIENT_SECRET no .env' },
            amazon: { name: 'Amazon', status: 'loading' },
            shopee: { name: 'Shopee', status: 'blocked', message: 'A loja pediu verificação (captcha/login)' },
          }}
        />
        <div className={styles.grid3}>
          <OfferCard offer={SAMPLE_OFFER} best />
          <OfferCard offer={SAMPLE_OFFER_2} />
        </div>
      </Section>
    </div>
  );
}
