// The formatters (PHASE_3.md 3.7 (l), test group 10): pure, no DOM.
import { describe, expect, it } from 'vitest';
import { closedChips, dayAndMonth, featureChips, formatEntry, formatFee, formatFloor, formatPrice, israelTime, kindLine, locationLine, phoneLabel, photoPosition, publishedTimes, relativeTime, roomsClosed, roomsOpen, sizeClosed, sizeOpen, } from './format';
const w = (value) => ({ state: 'written', value });
const NW = { state: 'not_written', value: null };
const UN = { state: 'unclear', value: null };
describe('rooms', () => {
    it('reads "1/N" on a closed room card (#325), halves kept', () => {
        expect(roomsClosed('room', w(2.5))).toEqual({ text: '1/2.5' });
        expect(roomsClosed('room', w(4))).toEqual({ text: '1/4' });
    });
    it('reads "1" with a grey "total not stated" when the total is not written (#332)', () => {
        expect(roomsClosed('room', NW)).toEqual({ text: '1', note: 'סה״כ לא צוין' });
    });
    it('reads "1 of N" inside a room post, and a room with no "of" (#120)', () => {
        expect(roomsOpen('room', w(3)).text).toBe('חדר 1 מתוך 3');
        expect(roomsOpen('room', NW).text).toBe('חדר');
    });
    it('reads the total on a whole apartment, "לא צוין" when not written (#321)', () => {
        expect(roomsClosed('whole_apartment', w(3.5))).toEqual({ text: '3.5' });
        expect(roomsOpen('whole_apartment', w(3.5)).text).toBe('3.5 חדרים');
        expect(roomsClosed('whole_apartment', NW)).toEqual({ text: 'לא צוין', missing: true });
        expect(roomsClosed('whole_apartment', UN)).toEqual({ text: 'לא ברור' });
    });
});
describe('the room size (#99, #121)', () => {
    it('names the room and the apartment on a room post', () => {
        expect(sizeOpen('room', w(80), w(12)).text).toBe('12 מ״ר לחדר, מתוך 80');
        expect(sizeOpen('room', NW, w(12)).text).toBe('12 מ״ר לחדר');
        expect(sizeOpen('room', w(80), NW).text).toBe('80 מ״ר (כל הדירה)');
        expect(sizeOpen('room', NW, NW)).toEqual({ text: 'לא צוין', missing: true });
    });
    it("fits the closed card's narrow stat", () => {
        expect(sizeClosed('room', w(80), w(12)).text).toBe('12/80');
        expect(sizeClosed('room', NW, w(12))).toEqual({ text: '12' });
        expect(sizeClosed('room', w(80), NW)).toEqual({ text: '80', note: 'כל הדירה' });
        expect(sizeClosed('whole_apartment', w(65), NW).text).toBe('65');
        expect(sizeOpen('whole_apartment', w(65), w(12)).text).toBe('65 מ״ר');
    });
});
describe('"X/Y"', () => {
    it('shows every price as written (#95)', () => {
        expect(formatPrice(w([5000]))).toBe('₪5,000');
        expect(formatPrice(w([5000, 5500]))).toBe('₪5,000/5,500');
        expect(formatPrice(NW)).toBeNull();
        expect(formatPrice(UN)).toBe('המחיר לא ברור');
    });
    it('shows the floor of the floors only when the floors are written (#98, #106)', () => {
        expect(formatFloor(w(3), w(5)).text).toBe('3/5');
        expect(formatFloor(w(3), NW).text).toBe('3');
        expect(formatFloor(w(0), w(4)).text).toBe('קרקע/4');
        expect(formatFloor(w(-1), NW).text).toBe('מרתף');
        expect(formatFloor(NW, w(4))).toEqual({ text: 'לא צוין', missing: true });
    });
});
describe('the entry date: never its year (#96, #115)', () => {
    it('shows the text as the poster wrote it', () => {
        expect(formatEntry({ entry_date: w('2026-11-01'), entry_date_written: '1.11' })).toBe('1.11');
        expect(formatEntry({ entry_date: w('immediate'), entry_date_written: 'מיידית' })).toBe('מיידית');
    });
    it('shows a date with no text as day and month only', () => {
        expect(formatEntry({ entry_date: w('2027-02-15'), entry_date_written: null })).toBe('15.2');
        expect(dayAndMonth('2026-11-01')).toBe('1.11');
        expect(formatEntry({ entry_date: w('immediate'), entry_date_written: null })).toBe('כניסה מיידית');
    });
    it('is null when not written: the card shows the important-missing badge', () => {
        expect(formatEntry({ entry_date: NW, entry_date_written: null })).toBeNull();
    });
});
describe('relative time (#122)', () => {
    const now = new Date('2026-10-13T12:00:00Z');
    const before = (ms) => new Date(now.getTime() - ms).toISOString();
    const MIN = 60_000;
    it('counts minutes up to an hour', () => {
        expect(relativeTime(before(20_000), now)).toBe('עכשיו');
        expect(relativeTime(before(MIN), now)).toBe('לפני דקה');
        expect(relativeTime(before(2 * MIN), now)).toBe('לפני שתי דקות');
        expect(relativeTime(before(59 * MIN), now)).toBe('לפני 59 דקות');
    });
    it('counts hours up to 24 hours', () => {
        expect(relativeTime(before(60 * MIN), now)).toBe('לפני שעה');
        expect(relativeTime(before(120 * MIN), now)).toBe('לפני שעתיים');
        expect(relativeTime(before(23 * 60 * MIN + 59 * MIN), now)).toBe('לפני 23 שעות');
    });
    it('counts days after that', () => {
        expect(relativeTime(before(24 * 60 * MIN), now)).toBe('לפני יום');
        expect(relativeTime(before(48 * 60 * MIN), now)).toBe('לפני יומיים');
        expect(relativeTime(before(7 * 24 * 60 * MIN), now)).toBe('לפני 7 ימים');
    });
    it('never reads a time in the future as negative', () => {
        expect(relativeTime(new Date(now.getTime() + 5 * MIN).toISOString(), now)).toBe('עכשיו');
    });
});
describe('the rest of the card', () => {
    it('converts to Israel time at display only (invariant 9)', () => {
        expect(israelTime('2026-10-13T09:00:00+00:00')).toBe('13.10, 12:00'); // summer time, +3
        expect(israelTime('2026-12-01T22:30:00Z')).toBe('2.12, 00:30'); // winter, +2, the next day
    });
    it('says "published N times" only after a repost (#340)', () => {
        expect(publishedTimes(1)).toBeNull();
        expect(publishedTimes(3)).toBe('פורסם 3 פעמים');
    });
    it('numbers the carousel "1/5"', () => {
        expect(photoPosition(0, 5)).toBe('1/5');
    });
    it('shows a phone as name-number', () => {
        expect(phoneLabel('0541234567', 'דני')).toBe('דני-0541234567');
        expect(phoneLabel('0541234567', null)).toBe('0541234567');
    });
    it('says the kind and marks an unclear one with the option it is shown as (#273, #332, #339)', () => {
        expect(kindLine('whole_apartment', false, 'whole_apartment', false).text).toBe('דירה שלמה');
        expect(kindLine('room', false, 'room', true).text).toBe('חדר בדירת שותפים · סאבלט');
        expect(kindLine(null, true, 'room', false)).toEqual({ text: 'סוג לא ברור · מוצג כ: חדר', unclear: true });
    });
    it('writes the location line (#110, #321)', () => {
        const area = { number: 30, name: 'הצפון הישן' };
        expect(locationLine({ areas: [area], streets: ['דיזנגוף'], stated_area_names: [] })).toBe('הצפון הישן · דיזנגוף');
        expect(locationLine({ areas: [], streets: ['סנפיר'], stated_area_names: [] })).toBe('האזור לא ברור · סנפיר');
        expect(locationLine({ areas: [], streets: [], stated_area_names: [] })).toBe('מיקום: לא צוין');
    });
    it('writes arnona and the house committee', () => {
        expect(formatFee(w(450)).text).toBe('₪450');
        expect(formatFee(w('included')).text).toBe('כלול');
        expect(formatFee(NW)).toEqual({ text: 'לא צוין', missing: true });
    });
});
describe('the chips', () => {
    const fields = {
        broker: w(false),
        balcony: w(true),
        parking: NW,
        elevator: w(false),
        air_conditioning: UN,
        furnished: w('yes'),
    };
    it('names every value in words, never a glyph (#321, #323)', () => {
        expect(featureChips(fields).map((chip) => chip.text)).toEqual([
            'ללא תיווך',
            'מרפסת',
            'חניה: לא צוין',
            'אין מעלית',
            'מיזוג: לא ברור',
            'מרוהטת',
        ]);
    });
    it('keeps only the green chips on the closed card (#326)', () => {
        const colours = {
            broker: 'green',
            balcony: 'green',
            parking: 'grey',
            elevator: 'plain',
            air_conditioning: 'orange',
            furnished: 'plain',
        };
        expect(closedChips(fields, colours).map((chip) => chip.field)).toEqual(['broker', 'balcony']);
    });
});
