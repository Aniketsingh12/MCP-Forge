/**
 * The homepage signature: a looping scene that explains what MCP is and where
 * a generated server sits.
 *
 * An agent and an API sit either side of an empty socket — the gap you'd
 * normally have to fill by hand. The forge below consumes a spec, and a chip
 * (tools = its pins) rises and seats into the socket. The wires go live and a
 * tools/call round trip runs.
 *
 * Two arrangements share one stylesheet: a wide circuit for desktop and a
 * stacked one for phones, because scaling the wide layout down to 375px puts
 * the labels under 7px. Timing lives in index.css on one 13s timeline.
 */
export default function ForgeDiagram() {
  return (
    <>
      <WideScene />
      <StackedScene />
    </>
  );
}

const DESC =
  "An agent and an API separated by an empty socket. A spec enters the forge " +
  "and a generated MCP server rises to fill the socket, after which a " +
  "tools/call request flows from the agent through the server to the API and back.";

/** Shared gradients/filters — declared once, referenced by both scenes. */
function Defs() {
  return (
    <defs>
      <linearGradient id="fd-chip" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%" stopColor="#f9b767" />
        <stop offset="100%" stopColor="#d97706" />
      </linearGradient>
      <radialGradient id="fd-heat" cx="50%" cy="50%" r="50%">
        <stop offset="0%" stopColor="#f59e0b" stopOpacity="0.55" />
        <stop offset="100%" stopColor="#f59e0b" stopOpacity="0" />
      </radialGradient>
    </defs>
  );
}

/** Anvil echoing the wordmark. */
function Anvil({ x, y }: { x: number; y: number }) {
  return (
    <path
      className="fd-anvil"
      transform={`translate(${x} ${y})`}
      d="M0 0h72l-11 16h-50L0 0Z M26 16h20v14h-20z"
    />
  );
}

function Sparks({ x, y }: { x: number; y: number }) {
  return (
    <g className="fd-sparks">
      {[1, 2, 3, 4, 5].map((n) => (
        <circle
          key={n}
          className={`fd-spark fd-spark-${n}`}
          r={n % 2 ? 3 : 2.5}
          cx={x}
          cy={y}
        />
      ))}
    </g>
  );
}

/* ---------------------------------------------------------------- desktop */
function WideScene() {
  return (
    <svg
      className="fd fd-h"
      viewBox="0 0 920 470"
      role="img"
      aria-label={DESC}
      xmlns="http://www.w3.org/2000/svg"
    >
      <Defs />

      {/* wires: dashed while the gap is open, amber once the server seats */}
      <g className="fd-wire-idle">
        <path d="M220 175 H375" />
        <path d="M545 175 H700" />
      </g>
      <g className="fd-wire-live">
        <path d="M220 175 H375" />
        <path d="M545 175 H700" />
      </g>

      {/* the actual call on each hop */}
      <g className="fd-wire-label" fontSize="13">
        <text x="297" y="160" textAnchor="middle">
          tools/call
        </text>
        <text x="622" y="160" textAnchor="middle">
          GET /v1/charges
        </text>
      </g>
      <g className="fd-wire-sublabel" fontSize="11">
        <text x="297" y="203" textAnchor="middle">
          MCP · JSON-RPC
        </text>
        <text x="622" y="203" textAnchor="middle">
          HTTPS
        </text>
      </g>

      {/* request / response round trip */}
      <circle className="fd-pulse fd-pulse-1" r="5" cy="175" />
      <circle className="fd-pulse fd-pulse-2" r="5" cy="175" />
      <circle className="fd-pulse fd-pulse-3" r="5" cy="175" />
      <circle className="fd-pulse fd-pulse-4" r="5" cy="175" />

      <g className="fd-node">
        <rect x="50" y="120" width="170" height="110" rx="14" />
        <text className="fd-node-title" x="135" y="168" textAnchor="middle">
          Agent
        </text>
        <text className="fd-node-sub" x="135" y="192" textAnchor="middle">
          Claude · Cursor
        </text>
      </g>

      <g className="fd-node">
        <rect x="700" y="120" width="170" height="110" rx="14" />
        <text className="fd-node-title" x="785" y="168" textAnchor="middle">
          Your API
        </text>
        <text className="fd-node-sub" x="785" y="192" textAnchor="middle">
          Stripe · GitHub
        </text>
      </g>

      {/* the gap */}
      <g className="fd-socket">
        <rect x="375" y="120" width="170" height="110" rx="14" />
        <text className="fd-socket-label" x="460" y="181" textAnchor="middle">
          MCP server
        </text>
      </g>

      {/* forge */}
      <circle className="fd-heat" cx="460" cy="372" r="95" fill="url(#fd-heat)" />
      <g className="fd-forge">
        <rect x="392" y="332" width="136" height="80" rx="14" />
        <Anvil x={424} y={366} />
      </g>
      <text className="fd-forge-label" x="460" y="440" textAnchor="middle">
        MCP Forge
      </text>
      <Sparks x={460} y={356} />

      {/* the spec being consumed */}
      <g className="fd-spec">
        <rect x="150" y="342" width="86" height="62" rx="8" />
        <path d="M164 362h58 M164 374h58 M164 386h34" />
        <text className="fd-spec-label" x="193" y="422" textAnchor="middle">
          openapi.json
        </text>
      </g>

      {/* the forged server */}
      <g className="fd-chip">
        <g className="fd-pins">
          <rect className="fd-pin fd-pin-1" x="392" y="132" width="8" height="16" rx="2" />
          <rect className="fd-pin fd-pin-2" x="392" y="158" width="8" height="16" rx="2" />
          <rect className="fd-pin fd-pin-3" x="392" y="184" width="8" height="16" rx="2" />
          <rect className="fd-pin fd-pin-4" x="520" y="132" width="8" height="16" rx="2" />
          <rect className="fd-pin fd-pin-5" x="520" y="158" width="8" height="16" rx="2" />
          <rect className="fd-pin fd-pin-6" x="520" y="184" width="8" height="16" rx="2" />
        </g>
        <rect className="fd-chip-body" x="400" y="122" width="120" height="106" rx="10" />
        <text className="fd-chip-title" x="460" y="164" textAnchor="middle">
          server.py
        </text>
        <text className="fd-chip-sub" x="460" y="186" textAnchor="middle">
          6 tools
        </text>
      </g>
    </svg>
  );
}

/* ----------------------------------------------------------------- mobile */
function StackedScene() {
  return (
    <svg
      className="fd fd-v"
      viewBox="0 0 340 600"
      role="img"
      aria-label={DESC}
      xmlns="http://www.w3.org/2000/svg"
    >
      <Defs />

      <g className="fd-wire-idle">
        <path d="M170 92 V186" />
        <path d="M170 306 V400" />
      </g>
      <g className="fd-wire-live">
        <path d="M170 92 V186" />
        <path d="M170 306 V400" />
      </g>

      <g className="fd-wire-label" fontSize="13">
        <text x="182" y="145" textAnchor="start">
          tools/call
        </text>
        <text x="182" y="359" textAnchor="start">
          HTTPS
        </text>
      </g>

      {/* one down, one back — enough to read the round trip on a phone */}
      <circle className="fd-pulse fd-vpulse-1" r="5" cx="170" />
      <circle className="fd-pulse fd-vpulse-2" r="5" cx="170" />

      <g className="fd-node">
        <rect x="60" y="10" width="220" height="82" rx="14" />
        <text className="fd-node-title" x="170" y="46" textAnchor="middle">
          Agent
        </text>
        <text className="fd-node-sub" x="170" y="70" textAnchor="middle">
          Claude · Cursor
        </text>
      </g>

      <g className="fd-node">
        <rect x="60" y="400" width="220" height="82" rx="14" />
        <text className="fd-node-title" x="170" y="436" textAnchor="middle">
          Your API
        </text>
        <text className="fd-node-sub" x="170" y="460" textAnchor="middle">
          Stripe · GitHub
        </text>
      </g>

      <g className="fd-socket">
        <rect x="60" y="186" width="220" height="120" rx="14" />
        <text className="fd-socket-label" x="170" y="252" textAnchor="middle">
          MCP server
        </text>
      </g>

      <circle className="fd-heat" cx="170" cy="545" r="80" fill="url(#fd-heat)" />
      <g className="fd-forge">
        <rect x="102" y="510" width="136" height="72" rx="14" />
        <Anvil x={134} y={538} />
      </g>
      <Sparks x={170} y={532} />

      <g className="fd-chip">
        <g className="fd-pins">
          <rect className="fd-pin fd-pin-1" x="52" y="204" width="8" height="16" rx="2" />
          <rect className="fd-pin fd-pin-2" x="52" y="238" width="8" height="16" rx="2" />
          <rect className="fd-pin fd-pin-3" x="52" y="272" width="8" height="16" rx="2" />
          <rect className="fd-pin fd-pin-4" x="280" y="204" width="8" height="16" rx="2" />
          <rect className="fd-pin fd-pin-5" x="280" y="238" width="8" height="16" rx="2" />
          <rect className="fd-pin fd-pin-6" x="280" y="272" width="8" height="16" rx="2" />
        </g>
        <rect className="fd-chip-body" x="60" y="186" width="220" height="120" rx="10" />
        <text className="fd-chip-title" x="170" y="238" textAnchor="middle">
          server.py
        </text>
        <text className="fd-chip-sub" x="170" y="262" textAnchor="middle">
          6 tools
        </text>
      </g>
    </svg>
  );
}
