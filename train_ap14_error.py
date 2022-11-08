from cmath import log
import numpy as np
# %load_ext autoreload
# %autoreload 2
import time
import torch
from torch import nn
from torch.utils.data import DataLoader
from transformer import TransformerReg, loglikelihood
from data import ASPCAP_error

    

if __name__ == "__main__":
    #=========================Data loading ================================
    data_dir = "/data/jdli/sdss/"
    tr_file = "hogg19_spec_tr.npy"

    device = torch.device('cuda:1')
    TOTAL_NUM = 6000
    BATCH_SIZE = 3

    aspcap  = ASPCAP_error(data_dir+tr_file, total_num=TOTAL_NUM,
    part_train=False, device=device)

    # aspcap_val = ASPCAP(data_dir+val_file, device=device)
    train_size = int(0.5*len(aspcap))
    val_size = len(aspcap) - train_size
    train_dataset, val_dataset = torch.utils.data.random_split(aspcap, [train_size, val_size], generator=torch.Generator().manual_seed(42))
    print(len(train_dataset), len(val_dataset))

    # tr_loader  = DataLoader(train_dataset, batch_size=BATCH_SIZE, )
    # val_loader = DataLoader(val_dataset,  batch_size=BATCH_SIZE, )
    tr_loader = DataLoader(val_dataset, batch_size=BATCH_SIZE, )

    ##==================Model parameters============================
    ##==============================================================
    #===============================================================

    dim_val = 64 # This can be any value divisible by n_heads. 512 is used in the original transformer paper.
    n_heads = 4 # The number of attention heads (aka parallel attention layers). dim_val must be divisible by this number
    n_decoder_layers = 2 # Number of times the decoder layer is stacked in the decoder
    n_encoder_layers = 2 # Number of times the encoder layer is stacked in the encoder
    input_size = 1 # The number of input variables. 1 if univariate forecasting.
    enc_seq_len = 8575 # length of input given to encoder. Can have any integer value.
    dec_seq_len = 2 # length of input given to decoder. Can have any integer value.
    output_sequence_length = 2 # Length of the target sequence, i.e. how many time steps should your forecast
    max_seq_len = 8575 # What's the longest sequence the model will encounter? Used to make the positional encoder
    model = TransformerReg(dim_val=dim_val, input_size=input_size, 
                        batch_first=True, dec_seq_len=dec_seq_len, 
                        out_seq_len=output_sequence_length, n_decoder_layers=n_decoder_layers,
                        n_encoder_layers=n_encoder_layers, n_heads=n_heads,
                        max_seq_len=max_seq_len,
                        ).to(device)

    # criterion = nn.MSELoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=1e-3)

    total_loss = 0.
    num_epochs = 20
    # num_batches = train_size//BATCH_SIZE
    itr = 1
    num_iters  = 50
    
    for epoch in range(num_epochs):
        model.train()
        
        for batch, (x, y) in enumerate(tr_loader):
            start = time.time()

            output = model(x, y)
            loss = loglikelihood(output, y)
            loss_value = loss.item()

            optimizer.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 0.5)
            optimizer.step()

            total_loss += loss.item()
            del x, y, output

            if itr%num_iters == 0:
                end = time.time()
                print(f"Epoch #%d  Iteration #%d  tr loss:%.4f time:%.2f s"%(epoch, itr, total_loss/itr, (end-start)*num_iters))
                    # writer.add_scalar('training loss = ',loss_value,epoch*itr)
                # model.eval()
                # total_val_loss = 0
                # with torch.no_grad():
                #     k=0
                #     for x, y in val_loader:
                #         output = model(x, y)
                #         loss = loglikelihood(output, y)
                #         total_val_loss += loss.item()
                #         k+=1
                #         del x, y, output
                # print("val loss:%.4f"%(total_val_loss/k))
            itr+=1

    torch.save(model.state_dict(), data_dir+"model/ap_prlx_trsfm_error221021B.pt")
    