import { useEffect, useMemo, useState } from "react";
import MeleeFrame, { Panel, PanelRow, Sep } from "../ui/MeleeFrame";
import MeleeButton from "../ui/MeleeButton";
import { fmt } from "../../lib/utils";

/**
 * Modale Admin : Voir l'intégralité des joueurs, leurs stats, leur solde de Tilts,
 * et donner (ou retirer) des Tilts à un joueur, plusieurs joueurs, ou tous les inscrits d'un tournoi.
 */
/** @param {Record<string, any>} props */
export default function AdminUsersModal({
  open,
  onClose,
  players = [],
  tournaments = [],
  onAdjustTilt,
  onBulkAdjustTilt,
  onOpenTournamentCreate,
  onOpenShopAdmin,
}) {
  const [search, setSearch] = useState("");
  const [selectedIds, setSelectedIds] = useState([]);
  const [amount, setAmount] = useState(100);
  const [reason, setReason] = useState("Bonus Admin BDE");
  const [feedback, setFeedback] = useState("");

  const realPlayers = useMemo(
    () =>
      players
        .filter((pl) => !/^(bot_|cpu_|pnj_)/i.test(pl?.login || ""))
        .map((pl, idx) => ({ ...pl, rank: idx + 1 })),
    [players]
  );

  const realPlayerIdSet = useMemo(
    () => new Set(realPlayers.map((p) => p.id)),
    [realPlayers]
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

  const tournamentPresets = useMemo(
    () =>
      tournaments
        .map((t) => {
          const ids = (t.participants || [])
            .map((p) => p.user_id)
            .filter((uid) => realPlayerIdSet.has(uid));
          return {
            id: t.id,
            name: t.name,
            status: t.status,
            userIds: Array.from(new Set(ids)),
          };
        })
        .filter((t) => t.userIds.length > 0 || t.status === "registration" || t.status === "in_progress"),
    [tournaments, realPlayerIdSet]
  );

  useEffect(() => {
    if (!open) {
      setFeedback("");
      return;
    }
    if (selectedIds.length === 0 && realPlayers[0]?.id != null) {
      setSelectedIds([realPlayers[0].id]);
    }
  }, [open, realPlayers, selectedIds.length]);

  const selectedPlayers = useMemo(
    () => realPlayers.filter((p) => selectedIds.includes(p.id)),
    [realPlayers, selectedIds]
  );

  const currentPlayer =
    selectedPlayers.length === 1
      ? selectedPlayers[0]
      : selectedPlayers[0] || filtered[0] || realPlayers[0] || null;

  const totalMatches = currentPlayer
    ? (currentPlayer.wins || 0) + (currentPlayer.losses || 0)
    : 0;
  const winRate = totalMatches
    ? Math.round((currentPlayer.wins / totalMatches) * 100)
    : 0;

  const numAmount = Number(amount) || 0;
  const targetCount = selectedPlayers.length;
  const canGive = Boolean(targetCount > 0 && numAmount !== 0 && reason.trim());

  const togglePlayer = (playerId, forceMulti = false) => {
    setFeedback("");
    setSelectedIds((prev) => {
      const exists = prev.includes(playerId);
      if (forceMulti || prev.length > 1) {
        if (exists) {
          const next = prev.filter((id) => id !== playerId);
          return next.length > 0 ? next : [playerId];
        }
        return [...prev, playerId];
      }
      if (exists && prev.length === 1) {
        return prev;
      }
      return [playerId];
    });
  };

  const selectGroup = (ids, defaultReason) => {
    setFeedback("");
    if (!ids || ids.length === 0) return;
    setSelectedIds(ids);
    if (defaultReason && (reason === "Bonus Admin BDE" || reason.startsWith("Tournoi : "))) {
      setReason(defaultReason);
    }
  };

  const handleGive = async (customAmount) => {
    const val = customAmount !== undefined ? Number(customAmount) : numAmount;
    const cleanReason = reason.trim() || "Bonus Admin BDE";
    if (targetCount === 0 || !val) return;

    const ids = selectedPlayers.map((p) => p.id);
    if (ids.length === 1 && onAdjustTilt) {
      await onAdjustTilt(ids[0], val, cleanReason);
    } else if (onBulkAdjustTilt) {
      await onBulkAdjustTilt(ids, val, cleanReason);
    } else if (onAdjustTilt) {
      for (const uid of ids) {
        await onAdjustTilt(uid, val, cleanReason);
      }
    }
    setFeedback(
      `✓ ${val > 0 ? `+${fmt(val)}` : fmt(val)} Tilts appliqués à ${ids.length} joueur${
        ids.length > 1 ? "s" : ""
      }`
    );
  };

  return (
    <MeleeFrame
      open={open}
      onClose={onClose}
      title="Admin · Joueurs"
      sideLabel="Tilts"
      caption={
        targetCount > 1
          ? `${targetCount} joueurs sélectionnés · ${
              numAmount > 0 ? `+${fmt(numAmount)}` : fmt(numAmount)
            } Tilts / joueur`
          : currentPlayer
          ? `${currentPlayer.display_name || currentPlayer.login} · ${fmt(currentPlayer.balance)} Tilts`
          : `${realPlayers.length} joueurs inscrits`
      }
    >
      <div className="mm-main" style={{ gap: "calc(.55 * var(--u))", padding: "0 calc(1 * var(--u)) 0 calc(2 * var(--u))" }}>
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

        <div style={{ display: "flex", flexWrap: "wrap", gap: "calc(.45 * var(--u))", alignItems: "center" }}>
          <button
            type="button"
            className="mm-field"
            style={{
              width: "auto",
              cursor: "pointer",
              fontSize: "calc(1.15 * var(--u))",
              padding: "calc(.35 * var(--u)) calc(.7 * var(--u))",
              borderColor:
                targetCount === realPlayers.length && realPlayers.length > 1 ? "#ffd000" : "#3a42e6",
              background:
                targetCount === realPlayers.length && realPlayers.length > 1
                  ? "rgba(255, 208, 0, .22)"
                  : "rgba(20, 24, 80, .6)",
            }}
            onClick={() =>
              selectGroup(
                realPlayers.map((p) => p.id),
                "Bonus Admin BDE"
              )
            }
          >
            👥 Tous les joueurs ({realPlayers.length})
          </button>

          {tournamentPresets.map((tp) => {
            const isAllSelected =
              tp.userIds.length > 0 &&
              tp.userIds.length === selectedIds.length &&
              tp.userIds.every((id) => selectedIds.includes(id));
            return (
              <button
                key={tp.id}
                type="button"
                disabled={tp.userIds.length === 0}
                className="mm-field"
                style={{
                  width: "auto",
                  cursor: tp.userIds.length > 0 ? "pointer" : "not-allowed",
                  opacity: tp.userIds.length > 0 ? 1 : 0.55,
                  fontSize: "calc(1.15 * var(--u))",
                  padding: "calc(.35 * var(--u)) calc(.7 * var(--u))",
                  borderColor: isAllSelected ? "#ffd000" : "#3a42e6",
                  background: isAllSelected
                    ? "rgba(255, 208, 0, .25)"
                    : "rgba(20, 24, 80, .65)",
                }}
                onClick={() => selectGroup(tp.userIds, `Tournoi : ${tp.name}`)}
              >
                🏆 Inscrits {tp.name} ({tp.userIds.length})
              </button>
            );
          })}

          {targetCount > 1 && currentPlayer && (
            <button
              type="button"
              className="mm-field"
              style={{
                width: "auto",
                cursor: "pointer",
                fontSize: "calc(1.15 * var(--u))",
                padding: "calc(.35 * var(--u)) calc(.7 * var(--u))",
                borderColor: "#f87171",
              }}
              onClick={() => setSelectedIds([currentPlayer.id])}
            >
              ✕ 1 seul joueur
            </button>
          )}
        </div>

        <input
          className="mm-field"
          style={{ padding: "calc(.55 * var(--u)) calc(1 * var(--u))", fontSize: "calc(1.45 * var(--u))" }}
          placeholder="Rechercher un joueur (login ou pseudo)... (clic case [✓] pour multi-sélection)"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />

        <div
          className="mm-list"
          style={{
            maxHeight: "calc(20.5 * var(--u))",
            overflowY: "auto",
            paddingRight: "calc(.4 * var(--u))",
          }}
        >
          {filtered.map((pl) => {
            const isSel = selectedIds.includes(pl.id);
            const plTotal = (pl.wins || 0) + (pl.losses || 0);
            const plRate = plTotal ? Math.round((pl.wins / plTotal) * 100) : 0;
            const avatarSrc =
              pl.avatar_url ||
              (pl.login ? `https://cdn.intra.42.fr/users/${pl.login}.jpg` : null);

            return (
              <div
                key={pl.id ?? pl.login}
                className={`mm-match${isSel ? " mm-on" : ""}`}
                style={{ padding: "calc(.55 * var(--u)) calc(.9 * var(--u))", cursor: "pointer" }}
                onClick={() => togglePlayer(pl.id, false)}
              >
                <div style={{ display: "flex", alignItems: "center", gap: "calc(.75 * var(--u))", minWidth: 0, flex: 1 }}>
                  <button
                    type="button"
                    title="Ajouter / retirer de la sélection multiple"
                    onClick={(e) => {
                      e.stopPropagation();
                      togglePlayer(pl.id, true);
                    }}
                    style={{
                      width: "calc(2 * var(--u))",
                      height: "calc(2 * var(--u))",
                      borderRadius: "calc(.35 * var(--u))",
                      border: `2px solid ${isSel ? "#ffd000" : "#5a63ff"}`,
                      background: isSel ? "#ffd000" : "rgba(10, 14, 50, .7)",
                      color: isSel ? "#080b2a" : "#fff",
                      fontWeight: 900,
                      fontSize: "calc(1.2 * var(--u))",
                      display: "inline-flex",
                      alignItems: "center",
                      justifyContent: "center",
                      cursor: "pointer",
                      flexShrink: 0,
                    }}
                  >
                    {isSel ? "✓" : "+"}
                  </button>
                  <span
                    style={{
                      fontWeight: 900,
                      fontStyle: "italic",
                      fontSize: "calc(1.35 * var(--u))",
                      minWidth: "calc(2.3 * var(--u))",
                      color: "#9aa0ff",
                    }}
                  >
                    #{pl.rank}
                  </span>
                  <span className="mm-bavatar" style={{ width: "calc(2.5 * var(--u))", height: "calc(2.5 * var(--u))" }}>
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
                        fontSize: "calc(1.6 * var(--u))",
                        overflow: "hidden",
                        textOverflow: "ellipsis",
                        whiteSpace: "nowrap",
                      }}
                    >
                      {pl.display_name || pl.login}{" "}
                      <span style={{ fontSize: "calc(1.15 * var(--u))", color: "#9aa0ff" }}>
                        (@{pl.login})
                      </span>
                    </div>
                    <div className="mm-match-info" style={{ fontSize: "calc(1.18 * var(--u))" }}>
                      {pl.wins}V · {pl.losses}D ({plRate}%) · {pl.tournaments} tournois ·{" "}
                      <b style={{ color: "#ffe58a" }}>{fmt(pl.balance)} Tilts</b>
                    </div>
                  </div>
                </div>
                <span className="mm-tri mm-tri--l" />
              </div>
            );
          })}
        </div>

        <div className="mm-btns" style={{ gap: "calc(.6 * var(--u))" }}>
          <MeleeButton
            text={
              targetCount > 1
                ? `${numAmount < 0 ? "Retirer" : "Donner"} (${targetCount})`
                : numAmount < 0
                ? "Retirer Tilts"
                : "Donner Tilts"
            }
            selected={canGive}
            disabled={!canGive}
            height={36}
            onClick={() => handleGive()}
          />
          <MeleeButton text="Retour" height={36} onClick={onClose} />
        </div>
      </div>

      {targetCount > 0 ? (
        <Panel>
          {targetCount > 1 ? (
            <>
              <span className="mm-ptag" style={{ color: "#ffe58a" }}>
                Distribution groupée
              </span>
              <span className="mm-pname" style={{ fontSize: "calc(1.85 * var(--u))" }}>
                {targetCount} joueurs ciblés
              </span>
              <PanelRow
                label="Par joueur"
                value={`${numAmount > 0 ? "+" : ""}${fmt(numAmount)} Tilts`}
              />
              <PanelRow
                label="Total"
                value={`${numAmount > 0 ? "+" : ""}${fmt(numAmount * targetCount)} Tilts`}
                gold
              />
            </>
          ) : (
            currentPlayer && (
              <>
                <span className="mm-ptag">
                  Rang #{currentPlayer.rank} · {winRate}% Victoires
                </span>
                <span
                  className="mm-pname"
                  style={{
                    fontSize: "calc(1.9 * var(--u))",
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
              </>
            )
          )}

          <Sep />

          <span className="mm-ptag">Donner / Retirer des Tilts</span>
          <div className="mm-seg" style={{ gap: "calc(.4 * var(--u))" }}>
            {[50, 100, 500, -100].map((v) => (
              <button
                key={v}
                type="button"
                className={numAmount === v ? "on" : ""}
                style={{ fontSize: "calc(1.25 * var(--u))", padding: "calc(.45 * var(--u)) 0" }}
                onClick={() => setAmount(v)}
              >
                {v > 0 ? `+${v}` : v}
              </button>
            ))}
          </div>

          <label className="mm-fieldwrap">
            <span className="mm-ptag">Montant par joueur (Tilts)</span>
            <input
              type="number"
              step={10}
              className="mm-field"
              style={{ fontSize: "calc(1.55 * var(--u))", padding: "calc(.5 * var(--u)) calc(.7 * var(--u))" }}
              value={amount}
              onChange={(e) => setAmount(Number(e.target.value))}
            />
          </label>

          <label className="mm-fieldwrap">
            <span className="mm-ptag">Motif</span>
            <input
              className="mm-field"
              style={{ fontSize: "calc(1.35 * var(--u))", padding: "calc(.5 * var(--u)) calc(.7 * var(--u))" }}
              value={reason}
              placeholder="Bonus Admin BDE"
              onChange={(e) => setReason(e.target.value)}
            />
          </label>

          {feedback && (
            <span
              style={{
                color: "#4ade80",
                fontWeight: 800,
                fontSize: "calc(1.2 * var(--u))",
                textAlign: "center",
              }}
            >
              {feedback}
            </span>
          )}
        </Panel>
      ) : (
        <Panel>
          <span className="mm-ptext">Sélectionne un ou plusieurs joueurs</span>
        </Panel>
      )}
    </MeleeFrame>
  );
}
