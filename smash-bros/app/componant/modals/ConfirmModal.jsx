import MeleeFrame from "../ui/MeleeFrame";
import MeleeButton from "../ui/MeleeButton";

/**
 * Confirmation oui / non.
 * Props : title ("Attention"), question, caption, yesLabel ("Oui"), noLabel ("Non"),
 *         defaultNo (true : « Non » en surbrillance), onYes, onNo, open
 */
/** @param {Record<string, any>} props */
export default function ConfirmModal({ title = "Attention", question, caption, yesLabel = "Oui", noLabel = "Non", defaultNo = true, onYes, onNo, open }) {
  return (
    <MeleeFrame open={open} onClose={onNo} title={title} caption={caption}>
      <div className="mm-center" style={{ gap: "calc(3 * var(--u))" }}>
        <span className="mm-big">{question}</span>
        <div className="mm-btns">
          <MeleeButton text={yesLabel} mirror selected={!defaultNo} height={56} onClick={onYes} />
          <MeleeButton text={noLabel} selected={defaultNo} height={56} onClick={onNo} />
        </div>
      </div>
    </MeleeFrame>
  );
}
