/**
 * MIK-A5 / natural intent resolver for the sixteen non-A4 renderer IDs.
 * The resolver does NOT modify math state, emit Evidence, calculate answers,
 * or bypass a renderer's existing domain action / validator.
 *
 * A5 candidate: pure, strict, independently typechecked. Not yet mounted
 * into the FE-1445 runtime branch. Based on A0's immutable action catalog.
 */

export const A5_RENDERER_IDS = [
  'number-input', 'formula-board', 'ten-frame', 'grouping-board',
  'money-board', 'bar-model', 'array-board', 'place-value',
  'sorting-board', 'number-line', 'ruler', 'direction-grid',
  'shape-canvas', 'pattern-board', 'shape-gallery', 'estimation-canvas'
] as const;
export type A5RendererId = typeof A5_RENDERER_IDS[number];

type Modality = 'pointer' | 'keyboard' | 'accessible-control';
export type A5Context = Readonly<{
  taskInstanceId: string;
  activeTaskInstanceId: string;
  uiRevision: string | number;
  activeUiRevision: string | number;
  disabled: boolean;
  modality: Modality;
}>;

export type A5Intent =
  | { rendererId: 'number-input'; text: string; integerOnly: boolean; maxLength: number }
  | { rendererId: 'formula-board'; slotId: string; activeSlotId: string | null;
      token: { kind: 'number'; digit: number } | { kind: 'operator'; symbol: string } }
  | { rendererId: 'ten-frame'; from: 'bank' | 'cell'; to: 'cell' | 'return-tray';
      frameIndex: number; cellIndex: number; cellOccupied: boolean }
  | { rendererId: 'grouping-board'; from: 'pool' | 'group'; to: 'group' | 'pool';
      groupIndex: number; groupCount: number; sourceHasItem: boolean }
  | { rendererId: 'money-board'; from: 'coin-bank' | 'wallet'; to: 'wallet' | 'return-tray';
      denominationJiao: number; allowedDenominationsJiao: readonly number[]; walletCount: number }
  | { rendererId: 'bar-model'; barIndex: number; delta: number; existingBlocks: number; maxBlocks: number }
  | { rendererId: 'array-board'; edge: 'row' | 'col'; delta: number;
      current: number; limit: number }
  | { rendererId: 'place-value'; sourcePoolIndex: number; pickedPoolIndex: number | null;
      targetSlotIndex: number; slotCount: number }
  | { rendererId: 'sorting-board'; sourceCardId: string; selectedCardId: string | null;
      targetCardId: string; cardIds: readonly string[] }
  | { rendererId: 'number-line'; currentTick: number; targetTick: number;
      minTick: number; maxTick: number }
  | { rendererId: 'ruler'; mark: 0 | 1; targetTick: number;
      tickMin: number; tickMax: number; allowedTickStep: number }
  | { rendererId: 'direction-grid'; current: { r: number; c: number };
      target: { r: number; c: number }; rows: number; cols: number }
  | { rendererId: 'shape-canvas'; point: { x: number; y: number };
      gridMinX: number; gridMaxX: number; gridMinY: number; gridMaxY: number }
  | { rendererId: 'pattern-board'; targetIndex: number; blankCount: number;
      token: string | number; palette: readonly (string | number)[]; locked: boolean }
  | { rendererId: 'shape-gallery'; sourceShapeId: string; selectedShapeId: string | null;
      target: 'home' | 'return-tray'; currentlyAtHome: boolean }
  | { rendererId: 'estimation-canvas'; estimate: number;
      min: number; max: number; step: number };

export const A5_DOMAIN_ACTIONS = {
  'number-input': ['text change', 'clear'],
  'formula-board': ['applyActivate', 'applyNumberKey', 'applyOperatorKey', 'applyClear'],
  'ten-frame': ['applyCell', 'applyMakeTen', 'applyBreakTen'],
  'grouping-board': ['applyAddGroup', 'applyRemoveGroup', 'applyAddItem', 'applyRemoveItem'],
  'money-board': ['applyAddCoin', 'applyRemoveCoin'],
  'bar-model': ['applyBarDelta'],
  'array-board': ['applyRowDelta', 'applyColDelta'],
  'place-value': ['applyPick', 'applySlot'],
  'sorting-board': ['applySelectCard', 'applySwap', 'applyUndoSwap'],
  'number-line': ['applyJump'],
  'ruler': ['applyPlaceMark', 'applyClearMarks'],
  'direction-grid': ['applyMoveTo', 'applyUndoStep'],
  'shape-canvas': ['applyAddPoint', 'applyRemoveLast'],
  'pattern-board': ['applyPlaceToken', 'applyReplaceAt', 'applyClearAt'],
  'shape-gallery': ['applySelect', 'applyPlaceHome', 'applyReturnHome'],
  'estimation-canvas': ['applyEstimate', 'applyReason']
} as const satisfies Record<A5RendererId, readonly string[]>;

type Primitive = string | number | boolean | null;
type Args = Readonly<Record<string, Primitive>>;
export type DomainCommand = Readonly<{
  rendererId: A5RendererId;
  operation: string;
  args: Args;
  /** Runtime domain adapter alone chooses the existing event from its action result. */
  evidenceOwner: 'existing-domain';
}>;
export type A5Resolution =
  | Readonly<{ status: 'ready'; command: DomainCommand }>
  | Readonly<{ status: 'cancelled' | 'blocked'; reason: string }>;

const ready = (rendererId: A5RendererId, operation: string, args: Args): A5Resolution => {
  if (!(A5_DOMAIN_ACTIONS[rendererId] as readonly string[]).includes(operation)) {
    return { status: 'blocked', reason: 'action-not-in-frozen-a0-catalog' };
  }
  return { status: 'ready', command: { rendererId, operation, args, evidenceOwner: 'existing-domain' } };
};
const block = (reason: string): A5Resolution => ({ status: 'blocked', reason });
const cancel = (reason: string): A5Resolution => ({ status: 'cancelled', reason });
const nat = (n: number): boolean => Number.isSafeInteger(n) && n >= 0;
const safe = (n: number): boolean => Number.isSafeInteger(n);
const within = (n: number, min: number, max: number): boolean =>
  Number.isFinite(n) && Number.isFinite(min) && Number.isFinite(max) && min <= max && n >= min && n <= max;
const name = (s: string): boolean => typeof s === 'string' && s.length > 0 && s.trim().length > 0;

/**
 * Interpret ONE completed accessible action / pointer release into ONE approved
 * domain operation. A domain result may still reject for mathematical reasons.
 * Invalid pointer targets must be passed as `null`, which cancels silently.
 * Not a scoring/readiness/evidence implementation.
 */
export function resolveNaturalIntent(
  intent: A5Intent | null,
  ctx: A5Context
): A5Resolution {
  if (ctx.disabled) return cancel('disabled');
  if (!name(ctx.taskInstanceId) || ctx.taskInstanceId !== ctx.activeTaskInstanceId)
    return cancel('task-instance-changed');
  if ((typeof ctx.uiRevision !== 'string' && typeof ctx.uiRevision !== 'number') ||
      ctx.uiRevision !== ctx.activeUiRevision)
    return cancel('ui-revision-changed');
  if (!intent) return cancel('outside-valid-target');

  switch (intent.rendererId) {
    case 'number-input': {
      if (ctx.modality === 'pointer') return block('number-input-has-no-drag-semantic');
      if (!safe(intent.maxLength) || intent.maxLength < 1 || intent.text.length > intent.maxLength)
        return block('invalid-length');
      if (intent.integerOnly && !/^-?\d*$/.test(intent.text)) return block('invalid-integer-text');
      if (!intent.integerOnly && !/^-?(?:\d+)?(?:\.\d*)?$/.test(intent.text))
        return block('invalid-number-text');
      return ready(intent.rendererId, 'text change', { text: intent.text });
    }
    case 'formula-board': {
      if (!name(intent.slotId) || intent.activeSlotId !== intent.slotId)
        return block('slot-must-be-explicitly-active-no-synthetic-selection');
      if (intent.token.kind === 'number') {
        if (!nat(intent.token.digit) || intent.token.digit > 9) return block('invalid-digit');
        return ready(intent.rendererId, 'applyNumberKey', { digit: intent.token.digit, slotId: intent.slotId });
      }
      if (intent.token.kind !== 'operator' || !name(intent.token.symbol)) return block('invalid-operator');
      return ready(intent.rendererId, 'applyOperatorKey', { symbol: intent.token.symbol, slotId: intent.slotId });
    }
    case 'ten-frame': {
      if (!nat(intent.frameIndex) || !nat(intent.cellIndex) || intent.cellIndex >= 10)
        return block('invalid-frame-cell');
      if (intent.from === 'bank' && intent.to === 'cell' && !intent.cellOccupied)
        return ready(intent.rendererId, 'applyCell', { frameIndex: intent.frameIndex, cellIndex: intent.cellIndex, action: 'fill' });
      if (intent.from === 'cell' && intent.to === 'return-tray' && intent.cellOccupied)
        return ready(intent.rendererId, 'applyCell', { frameIndex: intent.frameIndex, cellIndex: intent.cellIndex, action: 'remove' });
      return cancel('illegal-ten-frame-drop');
    }
    case 'grouping-board': {
      if (!nat(intent.groupCount) || !nat(intent.groupIndex) || intent.groupIndex >= intent.groupCount)
        return block('unknown-group');
      if (intent.from === 'pool' && intent.to === 'group')
        return ready(intent.rendererId, 'applyAddItem', { groupIndex: intent.groupIndex });
      if (intent.from === 'group' && intent.to === 'pool' && intent.sourceHasItem)
        return ready(intent.rendererId, 'applyRemoveItem', { groupIndex: intent.groupIndex });
      return cancel('illegal-group-drop');
    }
    case 'money-board': {
      const denomination = intent.denominationJiao;
      if (!nat(denomination) || denomination < 1 || !intent.allowedDenominationsJiao.includes(denomination))
        return block('denomination-not-in-config');
      if (intent.from === 'coin-bank' && intent.to === 'wallet')
        return ready(intent.rendererId, 'applyAddCoin', { denominationJiao: denomination });
      if (intent.from === 'wallet' && intent.to === 'return-tray' && nat(intent.walletCount) && intent.walletCount > 0)
        return ready(intent.rendererId, 'applyRemoveCoin', { denominationJiao: denomination });
      return cancel('illegal-coin-drop');
    }
    case 'bar-model': {
      if (!nat(intent.barIndex) || !nat(intent.existingBlocks) || !nat(intent.maxBlocks) ||
          intent.maxBlocks < 1 || (intent.delta !== 1 && intent.delta !== -1) ||
          intent.existingBlocks + intent.delta < 0 || intent.existingBlocks + intent.delta > intent.maxBlocks)
        return block('invalid-one-block-resize');
      return ready(intent.rendererId, 'applyBarDelta', { barIndex: intent.barIndex, delta: intent.delta });
    }
    case 'array-board': {
      if ((intent.edge !== 'row' && intent.edge !== 'col') ||
          !nat(intent.current) || !nat(intent.limit) || (intent.delta !== 1 && intent.delta !== -1) ||
          intent.current + intent.delta < 0 || intent.current + intent.delta > intent.limit)
        return block('array-edge-only-one-row-or-column');
      return ready(intent.rendererId, intent.edge === 'row' ? 'applyRowDelta' : 'applyColDelta', { delta: intent.delta });
    }
    case 'place-value': {
      if (!nat(intent.sourcePoolIndex) || !nat(intent.targetSlotIndex) ||
          !nat(intent.slotCount) || intent.targetSlotIndex >= intent.slotCount)
        return block('invalid-pool-or-slot');
      if (intent.pickedPoolIndex !== intent.sourcePoolIndex)
        return block('requires-existing-pick-domain-event');
      return ready(intent.rendererId, 'applySlot', { slotIndex: intent.targetSlotIndex });
    }
    case 'sorting-board': {
      if (!name(intent.sourceCardId) || !name(intent.targetCardId) ||
          !intent.cardIds.includes(intent.sourceCardId) || !intent.cardIds.includes(intent.targetCardId))
        return block('unknown-card');
      if (intent.selectedCardId !== intent.sourceCardId)
        return block('requires-existing-selection-no-synthetic-event');
      if (intent.sourceCardId === intent.targetCardId) return cancel('drop-on-same-card');
      return ready(intent.rendererId, 'applySwap', { targetCardId: intent.targetCardId });
    }
    case 'number-line': {
      if (!safe(intent.currentTick) || !safe(intent.targetTick) ||
          !safe(intent.targetTick - intent.currentTick) ||
          !safe(intent.minTick) || !safe(intent.maxTick) ||
          !within(intent.currentTick, intent.minTick, intent.maxTick) ||
          !within(intent.targetTick, intent.minTick, intent.maxTick))
        return block('invalid-number-line-tick');
      if (intent.targetTick === intent.currentTick) return cancel('zero-jump');
      return ready(intent.rendererId, 'applyJump', {
        fromTick: intent.currentTick, toTick: intent.targetTick, signedJump: intent.targetTick - intent.currentTick
      });
    }
    case 'ruler': {
      if ((intent.mark !== 0 && intent.mark !== 1) ||
          !safe(intent.targetTick) || !safe(intent.tickMin) || !safe(intent.tickMax) ||
          !safe(intent.allowedTickStep) || intent.allowedTickStep < 1 ||
          !within(intent.targetTick, intent.tickMin, intent.tickMax) ||
          (intent.targetTick - intent.tickMin) % intent.allowedTickStep !== 0)
        return block('tick-must-be-a-legal-mark');
      return ready(intent.rendererId, 'applyPlaceMark', { markIndex: intent.mark, tick: intent.targetTick });
    }
    case 'direction-grid': {
      const { current: a, target: b, rows, cols } = intent;
      if (!nat(rows) || !nat(cols) || rows < 1 || cols < 1 ||
          !nat(a.r) || !nat(a.c) || !nat(b.r) || !nat(b.c) ||
          a.r >= rows || a.c >= cols || b.r >= rows || b.c >= cols)
        return block('illegal-grid-cell');
      if (Math.abs(a.r - b.r) + Math.abs(a.c - b.c) !== 1)
        return cancel('not-one-orthogonal-step');
      return ready(intent.rendererId, 'applyMoveTo', { r: b.r, c: b.c });
    }
    case 'shape-canvas': {
      const p = intent.point;
      if (!safe(p.x) || !safe(p.y) || !safe(intent.gridMinX) || !safe(intent.gridMaxX) ||
          !safe(intent.gridMinY) || !safe(intent.gridMaxY) ||
          !within(p.x, intent.gridMinX, intent.gridMaxX) ||
          !within(p.y, intent.gridMinY, intent.gridMaxY))
        return cancel('outside-approved-canvas-grid');
      return ready(intent.rendererId, 'applyAddPoint', { x: p.x, y: p.y });
    }
    case 'pattern-board': {
      if (!nat(intent.blankCount) || !nat(intent.targetIndex) ||
          intent.targetIndex >= intent.blankCount || intent.locked)
        return cancel('pattern-slot-not-available');
      if (!((typeof intent.token === 'string' && name(intent.token)) ||
             (typeof intent.token === 'number' && Number.isFinite(intent.token))) ||
          !intent.palette.includes(intent.token)) return block('token-not-in-config-palette');
      return ready(intent.rendererId, 'applyReplaceAt', { blankIndex: intent.targetIndex, token: intent.token });
    }
    case 'shape-gallery': {
      if (!name(intent.sourceShapeId)) return block('invalid-shape-id');
      // A shape already at home may be returned directly: the original
      // applyReturnHome API does not require a synthetic selection event.
      if (intent.target === 'return-tray' && intent.currentlyAtHome)
        return ready(intent.rendererId, 'applyReturnHome', { shapeId: intent.sourceShapeId });
      if (intent.target === 'home' && !intent.currentlyAtHome &&
          intent.selectedShapeId === intent.sourceShapeId)
        return ready(intent.rendererId, 'applyPlaceHome', { shapeId: intent.sourceShapeId });
      if (intent.target === 'home') return block('requires-existing-shape-selection');
      return cancel('illegal-gallery-drop');
    }
    case 'estimation-canvas': {
      if (!safe(intent.estimate) || !safe(intent.min) || !safe(intent.max) ||
          !safe(intent.step) || !safe(intent.estimate - intent.min) ||
          intent.step < 1 || !within(intent.estimate, intent.min, intent.max) ||
          (intent.estimate - intent.min) % intent.step !== 0)
        return cancel('unsnapped-or-out-of-range-estimate');
      return ready(intent.rendererId, 'applyEstimate', { value: intent.estimate });
    }
    default: {
      const _exhaustive: never = intent;
      return _exhaustive;
    }
  }
}
