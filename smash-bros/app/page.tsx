"use client";

import SmashIntro from "./componant/ui/SmashIntro";
import MeleeButton from "./componant/ui/MeleeButton";

export default function Home() {
  return (
    <SmashIntro webmSrc="/smash-video.webm" mp4Src="/smash-video.mp4">
      <MeleeButton text="Connexion" href="/connexion"/>
    </SmashIntro>
  );
}