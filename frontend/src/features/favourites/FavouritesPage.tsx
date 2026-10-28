import { Link } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../../lib/api";
import type { ChargerCard } from "../../lib/types";
import { statusLabel } from "../../lib/format";
import { Badge, Button, Card, EmptyState, PageHeader, Skeleton, statusTone } from "../../components/ui";

export function FavouritesPage() {
  const queryClient = useQueryClient();
  const favourites = useQuery({ queryKey: ["favourites"], queryFn: () => api<{ items: ChargerCard[] }>("/favourites") });

  async function remove(id: string) {
    await api(`/favourites/${id}`, { method: "DELETE" });
    await queryClient.invalidateQueries({ queryKey: ["favourites"] });
  }

  return (
    <div className="space-y-4">
      <PageHeader title="Favourites" lede="Chargers you saved." />
      {favourites.isLoading ? <Skeleton /> : null}
      {favourites.data && favourites.data.items.length === 0 ? (
        <EmptyState title="No saved chargers" message="Open a charger and choose Save favourite." action={<Link className="font-semibold text-primary" to="/app/chargers">Find chargers</Link>} />
      ) : null}
      <div className="space-y-3">
        {favourites.data?.items.map((item) => (
          <Card key={item.id}>
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <h2 className="font-semibold">{item.display_name}</h2>
              </div>
              <Badge tone={statusTone(item.app_status)}>{statusLabel(item.app_status)}</Badge>
            </div>
            <div className="mt-3 flex gap-2">
              <Link to={`/app/chargers/${item.id}`}><Button type="button">Open</Button></Link>
              <Button variant="secondary" onClick={() => void remove(item.id)}>Remove</Button>
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}
