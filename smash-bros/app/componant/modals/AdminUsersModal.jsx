import { useEffect, useMemo, useState } from "react";
import MeleeFrame, { Panel, PanelRow, Sep } from "../ui/MeleeFrame";
import MeleeButton from "../ui/MeleeButton";
import { fmt } from "../../lib/utils";

/**
 * Modale Admin : Voir l'intégralité des joueurs, leurs stats, leur solde de Tilts,
 * et donner (ou retirer) des Tilts à n'importe quel joueur.
 */
export default function AdminUsersModal({
  open,
  onClose,
  players = [],
  onAdjustTilt,
  onOpenTournamentCreate,
  onOpenShopAdmin,
}) {
  const [search, setSearch] = useState("");
  const [selId, setSelId] = useState(null);
  const [amount, setAmount] = useState(100);
  const [reason, setReason] = useState("Bonus Admin BDE");

  const realPlayers = useMemo(
    () =>
      players
        .filter((pl) => !/^(bot_|cpu_|pnj_)/i.test(pl?.login || ""))
        .map((pl, idx) => ({ ...pl, rank: idx + 1 })),
    [players]
  );

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) return realPlayers;
    return realPlayers.filter(
      (p) =>
        (p.login || "").toLowerCase().includes(q) ||
        (p.display_name || "").toLowerCase().includes(q)
    );
  }, [realPlayers, search]);

  const currentPlayer =
    filtered.find((p) => p.id === selId) || filtered[0] || realPlayers[0] || null;

  useEffect(() => {
    if (open && currentPlayer && selId == null) {
      setSelId(currentPlayer.id);
    }
  }, [open, currentPlayer?.id, selId]);

  const totalMatches = currentPlayer
    ? (currentPlayer.wins || 0) + (currentPlayer.losses || 0)
    : 0;
  const winRate = totalMatches
    ? Math.round((currentPlayer.wins / totalMatches) * 100)
    : 0;

  const numAmount = Number(amount) || 0;
  const canGive = Boolean(currentPlayer?.id && numAmount !== 0 && reason.trim());

  const handleGive = async (customAmount) => {
    const val = customAmount !== undefined ? Number(customAmount) : numAmount;
    if (!currentPlayer?.id || !val) return;
    await onAdjustTilt?.(
      currentPlayer.id,
      val,
      reason.trim() || "Bonus Admin BDE"
    );
  };

  return (
    <MeleeFrame
      open={open}
      onClose={onClose}
      title="Admin · Joueurs"
      sideLabel="Tilts"
      caption={
        currentPlayer
          ? `${currentPlayer.display_name || currentPlayer.login} · ${fmt(currentPlayer.balance)} Tilts`
          : `${realPlayers.length} joueurs inscrits`
      }
    >
      <div className="mm-main" style={{ gap: ".7cqw", padding: "0 1cqw 0 2cqw" }}>
        <div className="mm-seg">
          {onOpenTournamentCreate && (
            <button type="button" onClick={onOpenTournamentCreate}>
              Nouveau Tournoi
            </button>
          )}
          {onOpenShopAdmin && (
            <button type="button" onClick={onOpenShopAdmin}>
              Gérer le Shop
            </button>
          )}
          <button type="button" className="on">
            Joueurs & Tilts
          </button>
        </div>

        <input
          className="mm-field"
          style={{ padding: ".6cqw 1cqw", fontSize: "1.5cqw" }}
          placeholder="Rechercher un joueur (login ou pseudo)..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />

        <div
          className="mm-list"
          style={{
            maxHeight: "23.5cqw",
            overflowY: "auto",
            paddingRight: ".4cqw",
          }}
        >
          {filtered.map((pl) => {
            const isSel = currentPlayer?.id === pl.id;
            const plTotal = (pl.wins || 0) + (pl.losses || 0);
            const plRate = plTotal ? Math.round((pl.wins / plTotal) * 100) : 0;
            const avatarSrc =
              pl.avatar_url ||
              (pl.login ? `https://cdn.intra.42.fr/users/${pl.login}.jpg` : null);

            return (
              <button
                key={pl.id ?? pl.login}
                type="button"
                className={`mm-match${isSel ? " mm-on" : ""}`}
                style={{ padding: ".65cqw 1cqw" }}
                onClick={() => setSelId(pl.id)}
              >
                <div style={{ display: "flex", alignItems: "center", gap: ".8cqw", minWidth: 0 }}>
                  <span
                    style={{
                      fontWeight: 900,
                      fontStyle: "italic",
                      fontSize: "1.4cqw",
                      minWidth: "2.4cqw",
                      color: "#9aa0ff",
                    }}
                  >
                    #{pl.rank}
                  </span>
                  <span className="mm-bavatar" style={{ width: "2.6cqw", height: "2.6cqw" }}>
                    {avatarSrc ? (
                      <img src={avatarSrc} alt={pl.display_name || pl.login} />
                    ) : (
                      (pl.display_name || pl.login || "?").charAt(0).toUpperCase()
                    )}
                  </span>
                  <div style={{ minWidth: 0, flex: 1 }}>
                    <div
                      className="mm-match-title"
                      style={{
                        fontSize: "1.65cqw",
                        overflow: "hidden",
                        textOverflow: "ellipsis",
                        whiteSpace: "nowrap",
                      }}
                    >
                      {pl.display_name || pl.login}{" "}
                      <span style={{ fontSize: "1.15cqw", color: "#9aa0ff" }}>
                        (@{pl.login})
                      </span>
                    </div>
                    <div className="mm-match-info" style={{ fontSize: "1.2cqw" }}>
                      {pl.wins}V · {pl.losses}D ({plRate}%) · {pl.tournaments} tournois ·{" "}
                      <b style={{ color: "#ffe58a" }}>{fmt(pl.balance)} Tilts</b>
                    </div>
                  </div>
                </div>
                <span className="mm-tri mm-tri--l" />
              </button>
            );
          })}
        </div>

        <div className="mm-btns" style={{ gap: ".6cqw" }}>
          <MeleeButton
            text={numAmount < 0 ? "Retirer Tilts" : "Donner Tilts"}
            selected={canGive}
            disabled={!canGive}
            height={36}
            onClick={() => handleGive()}
          />
          <MeleeButton text="Retour" height={36} onClick={onClose} />
        </div>
      </div>

      {currentPlayer ? (
        <Panel>
          <span className="mm-ptag">
            Rang #{currentPlayer.rank} · {winRate}% Victoires
          </span>
          <span
            className="mm-pname"
            style={{
              fontSize: "1.9cqw",
              overflow: "hidden",
              textOverflow: "ellipsis",
              whiteSpace: "nowrap",
            }}
          >
            {currentPlayer.display_name || currentPlayer.login}
          </span>
          <PanelRow label="Solde" value={`${fmt(currentPlayer.balance)} Tilts`} gold />
          <PanelRow
            label="Bilan"
            value={`${currentPlayer.wins}V / ${currentPlayer.losses}D (${currentPlayer.tournaments} T)`}
          />

          <Sep />

          <span className="mm-ptag">Donner / Retirer des Tilts</span>
          <div className="mm-seg" style={{ gap: ".4cqw" }}>
            {[50, 100, 500, -100].map((v) => (
              <button
                key={v}
                type="button"
                className={numAmount === v ? "on" : ""}
                style={{ fontSize: "1.25cqw", padding: ".45cqw 0" }}
                onClick={() => setAmount(v)}
              >
                {v > 0 ? `+${v}` : v}
              </button>
            ))}
          </div>

          <label className="mm-fieldwrap">
            <span className="mm-ptag">Montant (Tilts)</span>
            <input
              type="number"
              step={10}
              className="mm-field"
              style={{ fontSize: "1.55cqw", padding: ".5cqw .7cqw" }}
              value={amount}
              onChange={(e) => setAmount(Number(e.target.value))}
            />
          </label>

          <label className="mm-fieldwrap">
            <span className="mm-ptag">Motif</span>
            <input
              className="mm-field"
              style={{ fontSize: "1.35cqw", padding: ".5cqw .7cqw" }}
              value={reason}
              placeholder="Bonus Admin BDE"
              onChange={(e) => setReason(e.target.value)}
            />
          </label>
        </Panel>
      ) : (
        <Panel>
          <span className="mm-ptext">Sélectionne un joueur</span>
        </Panel>
      )}
    </MeleeFrame>
  );
}
