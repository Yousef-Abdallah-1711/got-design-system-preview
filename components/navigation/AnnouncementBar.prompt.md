Rotating mono uppercase announcement strip above the header; burgundy accent by default.
```jsx
<AnnouncementBar messages={[{text:'Cash on delivery across Egypt'},{text:'Drop 01 — Explore the collection',key:'shop'},{text:'Forged to be different'}]} onSelect={m=>go(m.key)} />
<AnnouncementBar variant="dark">Drop 01 — Coming soon</AnnouncementBar>
```
- Only publish claims verified by store config. Use `variant="dark"` if burgundy proves overpowering.
