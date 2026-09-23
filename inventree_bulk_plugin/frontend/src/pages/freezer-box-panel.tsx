import { render } from "preact";
import { useEffect, useState } from "preact/hooks";
import { type InvenTreePluginContext } from "@inventreedb/ui";
import { Alert, Anchor, Button, Group, MantineProvider, Select, Stack, Table, Text, TextInput, Title } from "@mantine/core";
import "@mantine/core/styles.css";

interface Result {
  status: string;
  parent_path: string;
  box_name: string;
  position_count: number;
  positions: string[];
  box_url: string | null;
}

function FreezerBox({ context }: { context: InvenTreePluginContext }) {
  const [name, setName] = useState("");
  const [layout, setLayout] = useState("9x9");
  const [path, setPath] = useState("");
  const [preview, setPreview] = useState<Result | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const size = layout === "10x10" ? 10 : 9;
  const parent = Number(context.id);

  useEffect(() => {
    let cancelled = false;
    setPath(""); setPreview(null); setError("");
    context.api.get(`/api/stock/location/${parent}/`).then((response) => {
      if (!cancelled) setPath(response.data.pathstring);
    }).catch(() => { if (!cancelled) setError("Unable to load the rack-slot location. Reload this page to retry."); });
    return () => { cancelled = true; };
  }, [context.api, parent]);

  async function submit(create: boolean) {
    setBusy(true); setError("");
    try {
      const response = await context.api.post(`/plugin/inventree-bulk-plugin/bulkcreate?create=${create}`, {
        mode: "freezer_box", parent_id: parent, box_name: name, layout,
      }, { timeout: 120000 });
      setPreview(response.data);
    } catch (failure) {
      const detail = (failure as { response?: { data?: unknown } }).response?.data;
      setError(detail ? (typeof detail === "string" ? detail : JSON.stringify(detail)) : "Request failed. Preview again to check whether the box was created.");
      setPreview(null);
    } finally { setBusy(false); }
  }

  return <Stack maw={850}>
    <Title order={3}>Create freezer box</Title>
    <Text>Selected rack slot: <strong>{path || "Loading…"}</strong></Text>
    <Text size="sm">One box per slot. Creates empty stock locations for the box and its positions.</Text>
    <TextInput label="Box name" value={name} disabled={busy} required onChange={(event) => { setName(event.currentTarget.value); setPreview(null); }} />
    <Select label="Box layout" value={layout} disabled={busy} allowDeselect={false} data={[{ value: "9x9", label: "9 × 9 — 81 positions (A1–I9)" }, { value: "10x10", label: "10 × 10 — 100 positions (A1–J10)" }]} onChange={(value) => { setLayout(value || "9x9"); setPreview(null); }} />
    {error && <Alert color="red" title="Cannot create box">{error}</Alert>}
    <Group>
      <Button variant="light" disabled={!name.trim() || !path || busy} onClick={() => void submit(false)}>Preview</Button>
      <Button disabled={busy || preview?.status !== "ready"} loading={busy} onClick={() => void submit(true)}>Create freezer box</Button>
    </Group>
    {preview && <>
      <Alert color={preview.status === "ready" ? "blue" : "green"} title={preview.status === "created" ? "Box created" : preview.status === "already_exists" ? "Box already exists — unchanged" : "Ready to create"}>
        {preview.parent_path} / {preview.box_name} · {preview.position_count} positions
        {preview.box_url && <Text><Anchor href={preview.box_url}>Open box</Anchor></Text>}
      </Alert>
      <Table.ScrollContainer minWidth={500}><Table withTableBorder withColumnBorders>
        <Table.Thead><Table.Tr><Table.Th>Row</Table.Th>{Array.from({ length: size }, (_, c) => <Table.Th key={c}>{c + 1}</Table.Th>)}</Table.Tr></Table.Thead>
        <Table.Tbody>{Array.from({ length: size }, (_, r) => <Table.Tr key={r}><Table.Th>{String.fromCharCode(65 + r)}</Table.Th>{preview.positions.slice(r * size, (r + 1) * size).map((position) => <Table.Td key={position}>{position}</Table.Td>)}</Table.Tr>)}</Table.Tbody>
      </Table></Table.ScrollContainer>
    </>}
  </Stack>;
}

export function renderPanel(ref: HTMLDivElement, context: InvenTreePluginContext) {
  render(<MantineProvider theme={context.theme} forceColorScheme={context.colorScheme === "auto" ? undefined : context.colorScheme} getRootElement={() => ref}><FreezerBox context={context} /></MantineProvider>, ref);
}
