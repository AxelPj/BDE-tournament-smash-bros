import { useState } from "react";

/** Avatar rond d'un joueur (photo, sinon photo de l'intra 42, sinon initiale). */
/** @param {Record<string, any>} props */
export default function PlayerAvatar({ player }) {
  const [imgErr, setImgErr] = useState(false);
  if (!player) {
    return <span className="mm-bavatar">?</span>;
  }
  const src =
    !imgErr &&
    (player.avatar_url ||
      (player.username ? `https://cdn.intra.42.fr/users/${player.username}.jpg` : null));
  const initial = (player.display_name || player.username || "?").charAt(0).toUpperCase();

  return (
    <span className="mm-bavatar">
      {src ? (
        <img src={src} alt={player.display_name || player.username} onError={() => setImgErr(true)} />
      ) : (
        initial
      )}
    </span>
  );
}
