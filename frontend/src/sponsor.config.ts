export type SponsorChannel = {
  id: string;
  name: string;
  description: string;
  icon: 'emerald' | 'diamond' | 'qr' | 'github';
  url?: string;
  /** Import a local payment QR image and use its bundled URL here. */
  qrImage?: string;
  recipient?: string;
};

// Only add channels supplied by the project maintainer. No guessed payment accounts.
export const sponsorConfig: {
  repository: string;
  channels: SponsorChannel[];
} = {
  repository: 'https://github.com/hanxing-go/Design_workbench',
  channels: [],
};
